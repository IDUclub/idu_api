"""Territories indicators internal logic is defined here."""

from collections import defaultdict
from datetime import date
from typing import Callable

from geoalchemy2.functions import ST_AsEWKB
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from idu_api.common.db.entities import (
    indicators_dict,
    indicators_groups_data,
    measurement_units_dict,
    physical_object_types_dict,
    service_types_dict,
    soc_value_indicators_data,
    soc_values_dict,
    territories_data,
    territory_indicators_binds_data,
    territory_indicators_data,
    territory_types_dict,
)
from idu_api.urban_api.dto import (
    BinnedIndicatorValueDTO,
    IndicatorDTO,
    IndicatorValueDTO,
    ShortTerritoryIndicatorBindDTO,
    SocValueIndicatorValueDTO,
    TerritoryWithIndicatorsDTO,
)
from idu_api.urban_api.exceptions.logic.common import EntityNotFoundById
from idu_api.urban_api.logic.impl.helpers.utils import (
    check_existence,
    get_parent_region_id,
    include_child_territories_cte,
)
from idu_api.urban_api.utils.query_filters import CustomFilter, EqFilter, ILikeFilter, InFilter, apply_filters

func: Callable


async def get_indicators_by_territory_id_from_db(conn: AsyncConnection, territory_id: int) -> list[IndicatorDTO]:
    """Get indicators for a given territory."""

    if not await check_existence(conn, territories_data, conditions={"territory_id": territory_id}):
        raise EntityNotFoundById(territory_id, "territory")

    statement = (
        select(
            indicators_dict,
            measurement_units_dict.c.name.label("measurement_unit_name"),
            service_types_dict.c.name.label("service_type_name"),
            physical_object_types_dict.c.name.label("physical_object_type_name"),
        )
        .select_from(
            territory_indicators_data.join(
                indicators_dict,
                indicators_dict.c.indicator_id == territory_indicators_data.c.indicator_id,
            )
            .outerjoin(
                measurement_units_dict,
                indicators_dict.c.measurement_unit_id == measurement_units_dict.c.measurement_unit_id,
            )
            .outerjoin(service_types_dict, service_types_dict.c.service_type_id == indicators_dict.c.service_type_id)
            .outerjoin(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id == indicators_dict.c.physical_object_type_id,
            )
        )
        .where(territory_indicators_data.c.territory_id == territory_id)
    )

    result = (await conn.execute(statement)).mappings().all()

    return [IndicatorDTO(**indicator) for indicator in result]


async def get_indicator_values_by_territory_id_from_db(  # pylint: disable=too-many-arguments
    conn: AsyncConnection,
    territory_id: int,
    indicator_ids: set[int] | None,
    indicators_group_id: int | None,
    start_date: date | None,
    end_date: date | None,
    value_type: str | None,
    information_source: str | None,
    last_only: bool,
    include_child_territories: bool,
    cities_only: bool,
) -> list[BinnedIndicatorValueDTO]:
    """Get indicator values by territory id, optional indicator_ids, value_type, source and time period.

    Could be specified by last_only to get only last indicator values.
    """

    if not await check_existence(conn, territories_data, conditions={"territory_id": territory_id}):
        raise EntityNotFoundById(territory_id, "territory")

    statement = select(
        territory_indicators_data,
        indicators_dict.c.parent_id,
        indicators_dict.c.name_full,
        indicators_dict.c.level,
        indicators_dict.c.list_label,
        measurement_units_dict.c.measurement_unit_id,
        measurement_units_dict.c.name.label("measurement_unit_name"),
        territories_data.c.name.label("territory_name"),
        territory_indicators_binds_data.c.min_value.label("binned_min_value"),
        territory_indicators_binds_data.c.max_value.label("binned_max_value"),
    ).distinct()

    select_from = (
        territory_indicators_data.join(
            indicators_dict,
            indicators_dict.c.indicator_id == territory_indicators_data.c.indicator_id,
        )
        .outerjoin(
            measurement_units_dict,
            measurement_units_dict.c.measurement_unit_id == indicators_dict.c.measurement_unit_id,
        )
        .outerjoin(
            indicators_groups_data,
            indicators_groups_data.c.indicator_id == indicators_dict.c.indicator_id,
        )
        .join(
            territories_data,
            territories_data.c.territory_id == territory_indicators_data.c.territory_id,
        )
        .outerjoin(
            territory_indicators_binds_data,
            (territory_indicators_binds_data.c.indicator_id == indicators_dict.c.indicator_id)
            & (territory_indicators_binds_data.c.level == territories_data.c.level),
        )
    )

    if last_only:
        subquery = (
            select(
                territory_indicators_data.c.indicator_id,
                territory_indicators_data.c.value_type,
                territory_indicators_data.c.territory_id,
                func.max(func.date(territory_indicators_data.c.date_value)).label("max_date"),
            )
            .group_by(
                territory_indicators_data.c.indicator_id,
                territory_indicators_data.c.value_type,
                territory_indicators_data.c.territory_id,
            )
            .subquery()
        )

        select_from = select_from.join(
            subquery,
            (territory_indicators_data.c.indicator_id == subquery.c.indicator_id)
            & (territory_indicators_data.c.value_type == subquery.c.value_type)
            & (territory_indicators_data.c.date_value == subquery.c.max_date)
            & (territory_indicators_data.c.territory_id == subquery.c.territory_id),
        )

    parent_region_id = await get_parent_region_id(conn, territory_id)
    statement = statement.select_from(select_from).where(
        (
            (territory_indicators_binds_data.c.territory_id == parent_region_id)
            & territory_indicators_binds_data.c.min_value.isnot(None)
            & territory_indicators_binds_data.c.max_value.isnot(None)
        )
        | True
    )

    if include_child_territories:
        territories_cte = include_child_territories_cte(territory_id, cities_only)
        territory_filter = CustomFilter(
            lambda q: q.where(territory_indicators_data.c.territory_id.in_(select(territories_cte.c.territory_id)))
        )
    else:
        territory_filter = EqFilter(territory_indicators_data, "territory_id", territory_id)

    statement = apply_filters(
        statement,
        InFilter(territory_indicators_data, "indicator_id", indicator_ids),
        EqFilter(indicators_groups_data, "indicators_group_id", indicators_group_id),
        CustomFilter(
            lambda q: q.where(func.date(territory_indicators_data.c.date_value) >= start_date) if start_date else q
        ),
        CustomFilter(
            lambda q: q.where(func.date(territory_indicators_data.c.date_value) <= end_date) if end_date else q
        ),
        EqFilter(territory_indicators_data, "value_type", value_type),
        ILikeFilter(territory_indicators_data, "information_source", information_source),
        territory_filter,
    )

    result = (await conn.execute(statement)).mappings().all()

    return [BinnedIndicatorValueDTO(**indicator_value) for indicator_value in result]


async def get_indicator_values_by_parent_id_from_db(  # pylint: disable=too-many-arguments
    conn: AsyncConnection,
    parent_id: int | None,
    indicator_ids: set[int] | None,
    indicators_group_id: int | None,
    start_date: date | None,
    end_date: date | None,
    value_type: str | None,
    information_source: str | None,
    last_only: bool,
    with_binned: bool,
) -> tuple[list[TerritoryWithIndicatorsDTO], list[ShortTerritoryIndicatorBindDTO]]:
    """
    Get indicator values for child territories by parent id,
    with optional filters, and collect bindings.
    """
    if parent_id is not None:
        if not await check_existence(conn, territories_data, conditions={"territory_id": parent_id}):
            raise EntityNotFoundById(parent_id, "territory")

    statement = (
        select(
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            territory_types_dict.c.territory_type_id,
            territory_types_dict.c.name.label("territory_type_name"),
            territories_data.c.is_city,
            territories_data.c.level.label("territory_level"),
            ST_AsEWKB(territories_data.c.geometry).label("geometry"),
            ST_AsEWKB(territories_data.c.centre_point).label("centre_point"),
            territory_indicators_data,
            indicators_dict.c.parent_id,
            indicators_dict.c.name_full,
            indicators_dict.c.level,
            indicators_dict.c.list_label,
            measurement_units_dict.c.measurement_unit_id,
            measurement_units_dict.c.name.label("measurement_unit_name"),
        )
        .where(
            territories_data.c.parent_id == parent_id
            if parent_id is not None
            else territories_data.c.parent_id.is_(None)
        )
        .distinct()
    )

    if last_only:
        subquery = (
            select(
                territory_indicators_data.c.indicator_id,
                territory_indicators_data.c.value_type,
                territory_indicators_data.c.territory_id,
                func.max(func.date(territory_indicators_data.c.date_value)).label("max_date"),
            )
            .group_by(
                territory_indicators_data.c.indicator_id,
                territory_indicators_data.c.value_type,
                territory_indicators_data.c.territory_id,
            )
            .subquery()
        )

        join_expr = territory_indicators_data.join(
            subquery,
            (territory_indicators_data.c.indicator_id == subquery.c.indicator_id)
            & (territory_indicators_data.c.value_type == subquery.c.value_type)
            & (territory_indicators_data.c.date_value == subquery.c.max_date)
            & (territory_indicators_data.c.territory_id == subquery.c.territory_id),
        )
    else:
        join_expr = territory_indicators_data

    statement = statement.select_from(
        join_expr.join(indicators_dict, indicators_dict.c.indicator_id == territory_indicators_data.c.indicator_id)
        .outerjoin(
            measurement_units_dict,
            measurement_units_dict.c.measurement_unit_id == indicators_dict.c.measurement_unit_id,
        )
        .outerjoin(
            indicators_groups_data,
            indicators_groups_data.c.indicator_id == indicators_dict.c.indicator_id,
        )
        .join(territories_data, territories_data.c.territory_id == territory_indicators_data.c.territory_id)
        .join(
            territory_types_dict,
            territory_types_dict.c.territory_type_id == territories_data.c.territory_type_id,
        )
    )

    statement = apply_filters(
        statement,
        InFilter(territory_indicators_data, "indicator_id", indicator_ids),
        EqFilter(indicators_groups_data, "indicators_group_id", indicators_group_id),
        CustomFilter(
            lambda q: q.where(func.date(territory_indicators_data.c.date_value) >= start_date) if start_date else q
        ),
        CustomFilter(
            lambda q: q.where(func.date(territory_indicators_data.c.date_value) <= end_date) if end_date else q
        ),
        EqFilter(territory_indicators_data, "value_type", value_type),
        ILikeFilter(territory_indicators_data, "information_source", information_source),
    )

    result = (await conn.execute(statement)).mappings().all()

    if not result:
        return [], []

    territories = defaultdict(list)
    for row in result:
        territories[row.territory_id].append(row)

    territories_with_indicators = [
        TerritoryWithIndicatorsDTO(
            territory_id=territory_id,
            name=rows[0].territory_name,
            territory_type_id=rows[0].territory_type_id,
            territory_type_name=rows[0].territory_type_name,
            is_city=rows[0].is_city,
            geometry=rows[0].geometry,
            centre_point=rows[0].centre_point,
            indicators=[
                IndicatorValueDTO(**{k: v for k, v in row.items() if k in IndicatorValueDTO.fields()}) for row in rows
            ],
        )
        for territory_id, rows in territories.items()
    ]

    binned = []
    if parent_id is not None and with_binned:
        all_indicator_ids = {r.indicator_id for r in result}
        common_level = result[0].territory_level
        parent_region_id = await get_parent_region_id(conn, parent_id)

        statement = (
            select(
                territory_indicators_binds_data.c.min_value,
                territory_indicators_binds_data.c.max_value,
                indicators_dict.c.indicator_id,
                indicators_dict.c.name_full.label("indicator_name"),
                measurement_units_dict.c.name.label("measurement_unit_name"),
            )
            .select_from(
                territory_indicators_binds_data.join(
                    indicators_dict, indicators_dict.c.indicator_id == territory_indicators_binds_data.c.indicator_id
                ).join(
                    measurement_units_dict,
                    measurement_units_dict.c.measurement_unit_id == indicators_dict.c.measurement_unit_id,
                )
            )
            .where(
                territory_indicators_binds_data.c.territory_id == parent_region_id,
                territory_indicators_binds_data.c.level == common_level,
                territory_indicators_binds_data.c.indicator_id.in_(all_indicator_ids),
            )
        )
        binned = (await conn.execute(statement)).mappings().all()

    binned = [ShortTerritoryIndicatorBindDTO(**b) for b in binned]

    return territories_with_indicators, binned


async def get_soc_values_indicator_values_by_territory_id_from_db(
    conn: AsyncConnection,
    territory_id: int,
    year: int | None,
    last_only: bool,
    include_child_territories: bool,
    cities_only: bool,
) -> list[SocValueIndicatorValueDTO]:
    """Get social value indicator values by territory identifier.

    Could be specified by last_only to get only last indicator values.
    """

    if not await check_existence(conn, territories_data, conditions={"territory_id": territory_id}):
        raise EntityNotFoundById(territory_id, "territory")

    select_from = soc_value_indicators_data.join(
        soc_values_dict,
        soc_values_dict.c.soc_value_id == soc_value_indicators_data.c.soc_value_id,
    ).join(territories_data, territories_data.c.territory_id == soc_value_indicators_data.c.territory_id)

    if last_only:
        subquery = (
            select(
                soc_value_indicators_data.c.soc_value_id,
                soc_value_indicators_data.c.territory_id,
                func.max(soc_value_indicators_data.c.year).label("max_date"),
            )
            .group_by(
                soc_value_indicators_data.c.soc_value_id,
                soc_value_indicators_data.c.territory_id,
            )
            .subquery()
        )

        select_from = select_from.join(
            subquery,
            (soc_value_indicators_data.c.soc_value_id == subquery.c.soc_value_id)
            & (soc_value_indicators_data.c.territory_id == subquery.c.territory_id)
            & (soc_value_indicators_data.c.year == subquery.c.max_date),
        )

    statement = select(
        soc_value_indicators_data,
        soc_values_dict.c.name.label("soc_value_name"),
        territories_data.c.name.label("territory_name"),
    ).select_from(select_from)

    if include_child_territories:
        territories_cte = include_child_territories_cte(territory_id, cities_only)
        territory_filter = CustomFilter(
            lambda q: q.where(soc_value_indicators_data.c.territory_id.in_(select(territories_cte.c.territory_id)))
        )
    else:
        territory_filter = EqFilter(soc_value_indicators_data, "territory_id", territory_id)

    statement = apply_filters(
        statement,
        territory_filter,
        EqFilter(soc_value_indicators_data, "year", year),
    )

    result = (await conn.execute(statement)).mappings().all()

    return [SocValueIndicatorValueDTO(**indicator_value) for indicator_value in result]
