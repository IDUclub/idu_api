"""Indicators territories-related handlers are defined here."""

from datetime import date

from fastapi import HTTPException, Path, Query, Request
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from starlette import status

from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    BinnedIndicatorValue,
    Indicator,
    ShortTerritoryIndicatorBind,
    SocValueIndicatorValue,
    TerritoryWithBinnedIndicators,
    TerritoryWithIndicators,
)
from idu_api.urban_api.schemas.enums import ValueType
from idu_api.urban_api.schemas.geojson import GeoJSONResponse, TerritoriesWithBinnedIndicators

from .routers import territories_router


@territories_router.get(
    "/territory/{territory_id}/indicators",
    response_model=list[Indicator],
    status_code=status.HTTP_200_OK,
)
async def get_indicators_by_territory_id(
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
) -> list[Indicator]:
    """
    ## Get indicators for a given territory.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.

    ### Returns:
    - **list[Indicator]**: A list of indicators associated with the territory.

    ### Errors:
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    indicators = await territories_service.get_indicators_by_territory_id(territory_id)

    return [Indicator.from_dto(indicator) for indicator in indicators]


@territories_router.get(
    "/territory/{territory_id}/indicator_values/geojson",
    response_model=GeoJSONResponse[Feature[Geometry, TerritoryWithBinnedIndicators]] | TerritoriesWithBinnedIndicators,
    status_code=status.HTTP_200_OK,
)
async def get_indicator_values_with_geometry_by_territory_id(  # pylint: disable=too-many-arguments
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    indicator_ids: str | None = Query(None, description="list of identifiers separated by comma"),
    indicators_group_id: int | None = Query(None, description="to filter by indicator group (identifier)", gt=0),
    start_date: date | None = Query(None, description="lowest date included"),
    end_date: date | None = Query(None, description="highest date included"),
    value_type: ValueType = Query(None, description="to filter by value type"),
    information_source: str | None = Query(None, description="to filter by source"),
    last_only: bool = Query(True, description="to get last indicators"),
    centers_only: bool = Query(False, description="display only centers"),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithBinnedIndicators]] | TerritoriesWithBinnedIndicators:
    """
    ## Get indicator values for a given territory (for only one) in GeoJSON format.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **indicator_ids** (str | None, Query): Comma-separated list of indicator IDs to filter results.
    - **indicators_group_id** (int | None, Query): Filters results by indicator group.
    - **start_date** (date | None, Query): Filters results by the earliest date included.
    - **end_date** (date | None, Query): Filters results by the latest date included.
    - **value_type** (ValueType, Query): Filters results by value type.
    - **information_source** (str | None, Query): Filters results by information source.
    - **last_only** (bool, Query): If True, retrieves only the most recent indicator values (default: true).
    - **centers_only** (bool, Query): If True, returns only center points of geometries (default: false).

    ### Returns:
    - **GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]]**: Territory with list of indicators in
    geojson format.

    ### Errors:
    - **400 Bad Request**: If `indicator_ids` is specified in the wrong form.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if indicator_ids is not None:
        try:
            indicator_ids = {int(ind_id.strip()) for ind_id in indicator_ids.split(",")}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пожалуйста, укажите идентификаторы индикаторов в правильном формате, разделив их запятой.",
            ) from exc

    value_type_field = value_type.value if value_type is not None else None

    territory = await territories_service.get_indicator_values_with_geometry_by_territory_id(
        territory_id,
        indicator_ids,
        indicators_group_id,
        start_date,
        end_date,
        value_type_field,
        information_source,
        last_only,
    )

    return await GeoJSONResponse.from_list([territory.to_geojson_dict()], centers_only, save_centers=True)


@territories_router.get(
    "/territory/{territory_id}/indicator_values",
    response_model=list[BinnedIndicatorValue],
    status_code=status.HTTP_200_OK,
)
async def get_indicator_values_by_territory_id(  # pylint: disable=too-many-arguments
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    indicator_ids: str | None = Query(None, description="list of identifiers separated by comma"),
    indicators_group_id: int | None = Query(None, description="to filter by indicator group (identifier)", gt=0),
    start_date: date | None = Query(None, description="lowest date included"),
    end_date: date | None = Query(None, description="highest date included"),
    value_type: ValueType = Query(None, description="to filter by value type"),
    information_source: str | None = Query(None, description="to filter by source"),
    last_only: bool = Query(True, description="to get last indicators"),
    include_child_territories: bool = Query(False, description="to get from child territories"),
    cities_only: bool = Query(False, description="to get only for cities"),
) -> list[BinnedIndicatorValue]:
    """
    ## Get indicator values for a given territory.

    **WARNING:** Set `cities_only = True` only if you want to get entities from child territories.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **indicator_ids** (str | None, Query): Comma-separated list of indicator IDs to filter results.
    - **indicators_group_id** (int | None, Query): Filters results by indicator group.
    - **start_date** (date | None, Query): Filters results by the earliest date included.
    - **end_date** (date | None, Query): Filters results by the latest date included.
    - **value_type** (ValueType, Query): Filters results by value type.
    - **information_source** (str | None, Query): Filters results by information source.
    - **last_only** (bool, Query): If True, retrieves only the most recent indicator values (default: true).
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: false).
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).

    ### Returns:
    - **list[IndicatorValue]**: A list of indicator values matching the filters + binned min/max value.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False
    or the indicator_ids is specified in the wrong form.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    if indicator_ids is not None:
        try:
            indicator_ids = {int(ind_id.strip()) for ind_id in indicator_ids.split(",")}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пожалуйста, укажите идентификаторы индикаторов в правильном формате, разделив их запятой.",
            ) from exc

    value_type_field = value_type.value if value_type is not None else None

    indicator_values = await territories_service.get_indicator_values_by_territory_id(
        territory_id,
        indicator_ids,
        indicators_group_id,
        start_date,
        end_date,
        value_type_field,
        information_source,
        last_only,
        include_child_territories,
        cities_only,
    )

    return [BinnedIndicatorValue.from_dto(value) for value in indicator_values]


@territories_router.get(
    "/territory/indicator_values",
    response_model=GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]] | TerritoriesWithBinnedIndicators,
    status_code=status.HTTP_200_OK,
)
async def get_indicator_values_by_parent_id(  # pylint: disable=too-many-arguments
    request: Request,
    parent_id: int | None = Query(
        None, description="parent territory identifier, should be skipped to get top level territories", gt=0
    ),
    indicator_ids: str | None = Query(None, description="list id separated by commas"),
    indicators_group_id: int | None = Query(None, description="to filter by indicator group (identifier)", gt=0),
    start_date: date | None = Query(None, description="lowest date included"),
    end_date: date | None = Query(None, description="highest date included"),
    value_type: ValueType = Query(None, description="to filter by value type"),
    information_source: str | None = Query(None, description="to filter by source"),
    last_only: bool = Query(True, description="to get last indicators"),
    with_binned: bool = Query(False, description="to get summary bindings for each indicator"),
    centers_only: bool = Query(False, description="display only centers"),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]] | TerritoriesWithBinnedIndicators:
    """
    ## Get indicator values for child territories (only given territory's level + 1) in GeoJSON format.

    ### Parameters:
    - **parent_id** (int | None, Query): Unique identifier of the parent territory. If skipped, returns the
    highest level territories.
    - **indicator_ids** (str | None, Query): Comma-separated list of indicator IDs to filter results.
    - **indicators_group_id** (int | None, Query): Filters results by indicator group.
    - **start_date** (date | None, Query): Filters results by the earliest date included.
    - **end_date** (date | None, Query): Filters results by the latest date included.
    - **value_type** (ValueType, Query): Filters results by value type.
    - **information_source** (str | None, Query): Filters results by information source.
    - **last_only** (bool, Query): If True, retrieves only the most recent indicator values (default: true).
    - **with_binned** (bool, Query): If True, returns not only geojson, but also list of binned values
    for each indicator.
    - **centers_only** (bool, Query): If True, returns only center points of geometries (default: false).

    ### Returns:
    - **GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]]**: A GeoJSON response containing territories
    and their indicator values.
    - **TerritoriesWithBinnedIndicators**: If `with_binned` = True, returns geojson + summary list of binned values.

    ### Errors:
    - **400 Bad Request**: If the indicator_ids is specified in the wrong form.
    - **404 Not Found**: If the parent territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if indicator_ids is not None:
        try:
            indicator_ids = {int(ind_id.strip()) for ind_id in indicator_ids.split(",")}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пожалуйста, укажите идентификаторы индикаторов в правильном формате, разделив их запятой.",
            ) from exc

    value_type_field = value_type.value if value_type is not None else None

    territories, binned = await territories_service.get_indicator_values_by_parent_id(
        parent_id,
        indicator_ids,
        indicators_group_id,
        start_date,
        end_date,
        value_type_field,
        information_source,
        last_only,
        with_binned,
    )

    if with_binned:
        return TerritoriesWithBinnedIndicators(
            geojson=await GeoJSONResponse.from_list(
                [territory.to_geojson_dict() for territory in territories], centers_only, save_centers=True
            ),
            binned=[ShortTerritoryIndicatorBind.from_dto(b) for b in binned],
        )

    return await GeoJSONResponse.from_list(
        [territory.to_geojson_dict() for territory in territories], centers_only, save_centers=True
    )


@territories_router.get(
    "/territory/{territory_id}/soc_values/indicators",
    response_model=list[SocValueIndicatorValue],
    status_code=status.HTTP_200_OK,
)
async def get_soc_values_indicator_values_by_territory_id(
    request: Request,
    territory_id: int | None = Path(..., description="territory identifier", gt=0),
    year: int | None = Query(None, description="year when value was modeled (skip to get values for all years)", gt=0),
    last_only: bool = Query(True, description="to get last indicators"),
    include_child_territories: bool = Query(False, description="to get from child territories"),
    cities_only: bool = Query(False, description="to get only for cities"),
) -> list[SocValueIndicatorValue]:
    """
    ## Get social values indicator values for a given territory.

    **WARNING:** Set `cities_only = True` only if you want to get entities from child territories.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **year** (int, Query): Filter results by specified year.
    - **last_only** (int, Query): To get only the last indicator value for each social group's value (default: true).
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: false).
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).

    ### Returns:
    - **list[IndicatorValue]**: A list of indicator values matching the filters.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False
    or the indicator_ids is specified in the wrong form.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if last_only and year is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Пожалуйста, выберите либо конкретный год, либо last_only.",
        )

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    indicator_values = await territories_service.get_soc_values_indicator_values_by_territory_id(
        territory_id,
        year,
        last_only,
        include_child_territories,
        cities_only,
    )

    return [SocValueIndicatorValue.from_dto(value) for value in indicator_values]
