"""Unit tests for territory-related indicators objects are defined here."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from geoalchemy2.functions import ST_AsEWKB
from sqlalchemy import func, select

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
from idu_api.urban_api.dto import IndicatorDTO, IndicatorValueDTO, SocValueIndicatorValueDTO, TerritoryWithIndicatorsDTO
from idu_api.urban_api.exceptions.logic.common import EntityNotFoundById
from idu_api.urban_api.logic.impl.helpers.territories_indicators import (
    get_indicator_values_by_parent_id_from_db,
    get_indicator_values_by_territory_id_from_db,
    get_indicators_by_territory_id_from_db,
    get_soc_values_indicator_values_by_territory_id_from_db,
)
from idu_api.urban_api.logic.impl.helpers.utils import include_child_territories_cte
from idu_api.urban_api.schemas import Indicator, IndicatorValue, SocValueIndicatorValue, TerritoryWithIndicators
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from tests.urban_api.helpers.connection import MockConnection

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
async def test_get_indicators_by_territory_id_from_db(mock_conn: MockConnection):
    """Test the get_indicators_by_territory_id_from_db function."""

    # Arrange
    territory_id = 1
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

    # Act
    with patch("idu_api.urban_api.logic.impl.helpers.territories_indicators.check_existence") as mock_check_existence:
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await get_indicators_by_territory_id_from_db(mock_conn, territory_id)
    result = await get_indicators_by_territory_id_from_db(mock_conn, territory_id)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(isinstance(item, IndicatorDTO) for item in result), "Each item should be a IndicatorDTO."
    assert isinstance(Indicator.from_dto(result[0]), Indicator), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_indicator_values_by_territory_id_from_db(mock_conn: MockConnection):
    """Test the get_indicator_values_by_territory_id_from_db function."""

    # Arrange
    territory_id = 1
    filters = {
        "indicators_group_id": 1,
        "indicator_ids": {1},
        "start_date": date.today(),
        "end_date": date.today(),
        "value_type": "real",
        "information_source": "mock_string",
    }
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
    base_statement = (
        select(
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
        )
        .distinct()
        .where(
            (
                (territory_indicators_binds_data.c.territory_id == 1)
                & territory_indicators_binds_data.c.min_value.isnot(None)
                & territory_indicators_binds_data.c.max_value.isnot(None)
            )
            | True
        )
    )
    base_select_from = (
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
    last_only_select_from = base_select_from.join(
        subquery,
        (territory_indicators_data.c.indicator_id == subquery.c.indicator_id)
        & (territory_indicators_data.c.value_type == subquery.c.value_type)
        & (territory_indicators_data.c.date_value == subquery.c.max_date)
        & (territory_indicators_data.c.territory_id == subquery.c.territory_id),
    )
    statement = base_statement.select_from(base_select_from)
    last_only_statement = base_statement.select_from(last_only_select_from)
    statement_with_filters = statement.where(
        territory_indicators_data.c.indicator_id.in_([1]),
        indicators_groups_data.c.indicators_group_id == filters["indicators_group_id"],
        func.date(territory_indicators_data.c.date_value) >= filters["start_date"],
        func.date(territory_indicators_data.c.date_value) <= filters["end_date"],
        territory_indicators_data.c.value_type == filters["value_type"],
        territory_indicators_data.c.information_source.ilike(f"%{filters['information_source']}%"),
        territory_indicators_data.c.territory_id == territory_id,
    )
    territories_cte = include_child_territories_cte(territory_id, True)
    last_only_recursive_statement = last_only_statement.where(
        territory_indicators_data.c.territory_id.in_(select(territories_cte.c.territory_id))
    )
    statement = statement.where(territory_indicators_data.c.territory_id == territory_id)
    last_only_statement = last_only_statement.where(territory_indicators_data.c.territory_id == territory_id)

    # Act
    with patch("idu_api.urban_api.logic.impl.helpers.territories_indicators.check_existence") as mock_check_existence:
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await get_indicator_values_by_territory_id_from_db(
                mock_conn, territory_id, **filters, last_only=False, include_child_territories=True, cities_only=True
            )
    await get_indicator_values_by_territory_id_from_db(
        mock_conn,
        territory_id,
        None,
        None,
        None,
        None,
        None,
        None,
        last_only=True,
        include_child_territories=True,
        cities_only=True,
    )
    await get_indicator_values_by_territory_id_from_db(
        mock_conn,
        territory_id,
        None,
        None,
        None,
        None,
        None,
        None,
        last_only=True,
        include_child_territories=False,
        cities_only=False,
    )
    await get_indicator_values_by_territory_id_from_db(
        mock_conn,
        territory_id,
        None,
        None,
        None,
        None,
        None,
        None,
        last_only=False,
        include_child_territories=False,
        cities_only=False,
    )
    result = await get_indicator_values_by_territory_id_from_db(
        mock_conn, territory_id, **filters, last_only=False, include_child_territories=False, cities_only=False
    )

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(isinstance(item, IndicatorValueDTO) for item in result), "Each item should be a IndicatorValueDTO."
    assert isinstance(IndicatorValue.from_dto(result[0]), IndicatorValue), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.execute_mock.assert_any_call(str(last_only_statement))
    mock_conn.execute_mock.assert_any_call(str(statement_with_filters))
    mock_conn.execute_mock.assert_any_call(str(last_only_recursive_statement))


@pytest.mark.asyncio
async def test_get_indicator_values_by_parent_id_from_db(mock_conn: MockConnection):
    """Test the get_indicator_values_by_parent_id_from_db function."""

    # Arrange
    parent_id = 1
    filters = {
        "indicators_group_id": 1,
        "indicator_ids": {1},
        "start_date": date.today(),
        "end_date": date.today(),
        "value_type": "real",
        "information_source": "mock_string",
        "with_binned": False,
    }
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
            (
                territories_data.c.parent_id == parent_id
                if parent_id is not None
                else territories_data.c.parent_id.is_(None)
            ),
            territory_indicators_data.c.indicator_id.in_([1]),
            indicators_groups_data.c.indicators_group_id == filters["indicators_group_id"],
            func.date(territory_indicators_data.c.date_value) >= filters["start_date"],
            func.date(territory_indicators_data.c.date_value) <= filters["end_date"],
            territory_indicators_data.c.value_type == filters["value_type"],
            territory_indicators_data.c.information_source.ilike(f"%{filters['information_source']}%"),
        )
        .distinct()
    )
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
    last_only_statement = statement.select_from(
        territory_indicators_data.join(
            subquery,
            (territory_indicators_data.c.indicator_id == subquery.c.indicator_id)
            & (territory_indicators_data.c.value_type == subquery.c.value_type)
            & (territory_indicators_data.c.date_value == subquery.c.max_date)
            & (territory_indicators_data.c.territory_id == subquery.c.territory_id),
        )
        .join(
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
        .join(territories_data, territories_data.c.territory_id == territory_indicators_data.c.territory_id)
        .join(
            territory_types_dict,
            territory_types_dict.c.territory_type_id == territories_data.c.territory_type_id,
        )
    )
    statement = statement.select_from(
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
        .join(territories_data, territories_data.c.territory_id == territory_indicators_data.c.territory_id)
        .join(
            territory_types_dict,
            territory_types_dict.c.territory_type_id == territories_data.c.territory_type_id,
        )
    )

    # Act
    with patch("idu_api.urban_api.logic.impl.helpers.territories_indicators.check_existence") as mock_check_existence:
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await get_indicator_values_by_parent_id_from_db(mock_conn, parent_id, **filters, last_only=False)
    await get_indicator_values_by_parent_id_from_db(mock_conn, parent_id, **filters, last_only=True)
    result, _ = await get_indicator_values_by_parent_id_from_db(mock_conn, parent_id, **filters, last_only=False)
    geojson_result = await GeoJSONResponse.from_list([r.to_geojson_dict() for r in result], save_centers=True)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, TerritoryWithIndicatorsDTO) for item in result
    ), "Each item should be a TerritoryWithIndicatorsDTO."
    assert all(
        isinstance(indicator, IndicatorValueDTO) for item in result for indicator in item.indicators
    ), "Each item in list indicators should be a IndicatorValueDTO."
    assert isinstance(
        TerritoryWithIndicators(**geojson_result.features[0].properties), TerritoryWithIndicators
    ), "Couldn't create pydantic model from geojson properties."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.execute_mock.assert_any_call(str(last_only_statement))


@pytest.mark.asyncio
async def test_get_soc_values_indicator_values_by_territory_id_from_db(mock_conn: MockConnection):
    """Test the get_indicator_values_by_territory_id_from_db function."""

    # Arrange
    territory_id = 1

    async def check_territory(conn, table, conditions):
        if table == territories_data:
            return False
        return True

    select_from = soc_value_indicators_data.join(
        soc_values_dict,
        soc_values_dict.c.soc_value_id == soc_value_indicators_data.c.soc_value_id,
    ).join(territories_data, territories_data.c.territory_id == soc_value_indicators_data.c.territory_id)
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
    last_only_select_from = select_from.join(
        subquery,
        (soc_value_indicators_data.c.soc_value_id == subquery.c.soc_value_id)
        & (soc_value_indicators_data.c.territory_id == subquery.c.territory_id)
        & (soc_value_indicators_data.c.year == subquery.c.max_date),
    )
    statement = (
        select(
            soc_value_indicators_data,
            soc_values_dict.c.name.label("soc_value_name"),
            territories_data.c.name.label("territory_name"),
        )
        .select_from(select_from)
        .where(soc_value_indicators_data.c.territory_id == territory_id)
    )
    last_only_statement = (
        select(
            soc_value_indicators_data,
            soc_values_dict.c.name.label("soc_value_name"),
            territories_data.c.name.label("territory_name"),
        )
        .select_from(last_only_select_from)
        .where(soc_value_indicators_data.c.territory_id == territory_id)
    )
    params = {"year": date.today().year, "include_child_territories": True, "cities_only": True}
    territories_cte = include_child_territories_cte(territory_id, cities_only=True)
    statement_with_filters = (
        select(
            soc_value_indicators_data,
            soc_values_dict.c.name.label("soc_value_name"),
            territories_data.c.name.label("territory_name"),
        )
        .select_from(select_from)
        .where(
            soc_value_indicators_data.c.territory_id.in_(select(territories_cte.c.territory_id)),
            soc_value_indicators_data.c.year == params["year"],
        )
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.territories_indicators.check_existence",
        new=AsyncMock(side_effect=check_territory),
    ):
        with pytest.raises(EntityNotFoundById):
            await get_soc_values_indicator_values_by_territory_id_from_db(
                mock_conn, territory_id, **params, last_only=False
            )
    await get_soc_values_indicator_values_by_territory_id_from_db(
        mock_conn, territory_id, None, last_only=False, include_child_territories=False, cities_only=False
    )
    await get_soc_values_indicator_values_by_territory_id_from_db(
        mock_conn, territory_id, None, last_only=True, include_child_territories=False, cities_only=False
    )
    result = await get_soc_values_indicator_values_by_territory_id_from_db(
        mock_conn, territory_id, last_only=False, **params
    )

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, SocValueIndicatorValueDTO) for item in result
    ), "Each item should be a SocValueIndicatorValueDTO."
    assert isinstance(
        SocValueIndicatorValue.from_dto(result[0]), SocValueIndicatorValue
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.execute_mock.assert_any_call(str(last_only_statement))
    mock_conn.execute_mock.assert_any_call(str(statement_with_filters))
