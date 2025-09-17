"""Physical objects territories-related handlers are defined here."""

from fastapi import HTTPException, Path, Query, Request
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from starlette import status

from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import PhysicalObject, PhysicalObjectType, PhysicalObjectWithGeometry
from idu_api.urban_api.schemas.enums import OrderByField, Ordering
from idu_api.urban_api.schemas.geometries import GeoJSONResponse
from idu_api.urban_api.schemas.pages import Page
from idu_api.urban_api.utils.pagination import paginate

from .routers import territories_router


@territories_router.get(
    "/territory/{territory_id}/physical_object_types",
    response_model=list[PhysicalObjectType],
    status_code=status.HTTP_200_OK,
)
async def get_physical_object_types_by_territory_id(
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    include_child_territories: bool = Query(True, description="to get from child territories"),
    cities_only: bool = Query(False, description="to get only for cities"),
) -> list[PhysicalObjectType]:
    """
    ## Get physical object types for a given territory.

    **WARNING:** Set `cities_only = True` only if you want to get entities from child territories.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: true).
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).

    ### Returns:
    - **list[PhysicalObjectType]**: A list of physical object types for the given territory.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    physical_object_types = await territories_service.get_physical_object_types_by_territory_id(
        territory_id, include_child_territories, cities_only
    )

    return [PhysicalObjectType.from_dto(service_type) for service_type in physical_object_types]


@territories_router.get(
    "/territory/{territory_id}/physical_objects",
    response_model=Page[PhysicalObject],
    status_code=status.HTTP_200_OK,
)
async def get_physical_objects_by_territory_id(
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    physical_object_type_id: int | None = Query(None, description="to filter by physical object type", gt=0),
    physical_object_function_id: int | None = Query(None, description="to filter by physical object function", gt=0),
    name: str | None = Query(None, description="filter physical objects by name substring (case-insensitive)"),
    include_child_territories: bool = Query(
        True, description="to get from child territories (unsafe for high level territories)"
    ),
    cities_only: bool = Query(False, description="to get only for cities"),
    order_by: OrderByField = Query(  # should be Optional, but swagger is generated wrongly then
        None, description="attribute to set ordering (created_at or updated_at)"
    ),
    ordering: Ordering = Query(
        Ordering.ASC, description="order type (ascending or descending) if ordering field is set"
    ),
) -> Page[PhysicalObject]:
    """
    ## Get physical objects for a given territory.

    **WARNING 1:** Set `cities_only = True` only if you want to get entities from child territories.

    **WARNING 2:** You can only filter by physical object type or physical object function.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **physical_object_type_id** (int | None, Query): Filters results by physical object type.
    - **physical_object_function_id** (int | None, Query): Filters results by physical object function.
    - **name** (str | None, Query): Filters results by a case-insensitive substring match.
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: True).
      Note: This can be unsafe for high-level territories due to potential performance issues.
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).
    - **order_by** (PhysicalObjectsOrderByField, Query): Defines the sorting attribute - physical_object_id (default), created_at or updated_at.
    - **ordering** (Ordering, Query): Specifies sorting order - ascending (default) or descending.
    - **page** (int, Query): Specifies the page number for retrieving physical objects (default: 1).
    - **page_size** (int, Query): Defines the number of physical objects per page (default: 10).

    ### Returns:
    - **Page[PhysicalObject]**: A paginated list of physical objects.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False or
    set both `physical_object_type_id` and `physical_object_function_id`.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    if physical_object_type_id is not None and physical_object_function_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id.",
        )

    order_by_value = order_by.value if order_by is not None else None

    physical_objects = await territories_service.get_physical_objects_by_territory_id(
        territory_id,
        physical_object_type_id,
        physical_object_function_id,
        name,
        include_child_territories,
        cities_only,
        order_by_value,
        ordering.value,
        paginate=True,
    )

    return paginate(
        physical_objects.items,
        physical_objects.total,
        transformer=lambda x: [PhysicalObject.from_dto(item) for item in x],
    )


@territories_router.get(
    "/territory/{territory_id}/physical_objects_with_geometry",
    response_model=Page[PhysicalObjectWithGeometry],
    status_code=status.HTTP_200_OK,
)
async def get_physical_objects_with_geometry_by_territory_id(
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    physical_object_type_id: int | None = Query(None, description="to filter by physical object type", gt=0),
    physical_object_function_id: int | None = Query(None, description="to filter by physical object function", gt=0),
    name: str | None = Query(None, description="filter physical objects by name substring (case-insensitive)"),
    include_child_territories: bool = Query(
        True, description="to get from child territories (unsafe for high level territories)"
    ),
    cities_only: bool = Query(False, description="to get only for cities"),
    order_by: OrderByField = Query(  # should be Optional, but swagger is generated wrongly then
        None, description="attribute to set ordering (created_at or updated_at)"
    ),
    ordering: Ordering = Query(
        Ordering.ASC, description="order type (ascending or descending) if ordering field is set"
    ),
) -> Page[PhysicalObjectWithGeometry]:
    """
    ## Get physical objects with geometry for a given territory.

    **WARNING 1:** Set `cities_only = True` only if you want to get entities from child territories.

    **WARNING 2:** You can only filter by physical object type or physical object function.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **physical_object_type_id** (int | None, Query): Filters results by physical object type.
    - **physical_object_function_id** (int | None, Query): Filters results by physical object function.
    - **name** (str | None, Query): Filters results by a case-insensitive substring match.
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: True).
      Note: This can be unsafe for high-level territories due to potential performance issues.
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).
    - **order_by** (PhysicalObjectsOrderByField, Query): Defines the sorting attribute - physical_object_id (default), created_at or updated_at.
    - **ordering** (Ordering, Query): Specifies sorting order - ascending (default) or descending.
    - **page** (int, Query): Specifies the page number for retrieving physical objects (default: 1).
    - **page_size** (int, Query): Defines the number of physical objects per page (default: 10).

    ### Returns:
    - **Page[PhysicalObjectWithGeometry]**: A paginated list of physical objects.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False or
    set both `physical_object_type_id` and `physical_object_function_id`.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    if physical_object_type_id is not None and physical_object_function_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id.",
        )

    order_by_value = order_by.value if order_by is not None else None

    physical_objects = await territories_service.get_physical_objects_with_geometry_by_territory_id(
        territory_id,
        physical_object_type_id,
        physical_object_function_id,
        name,
        include_child_territories,
        cities_only,
        order_by_value,
        ordering.value,
        paginate=True,
    )

    return paginate(
        physical_objects.items,
        physical_objects.total,
        transformer=lambda x: [PhysicalObjectWithGeometry.from_dto(item) for item in x],
    )


@territories_router.get(
    "/territory/{territory_id}/physical_objects_geojson",
    response_model=GeoJSONResponse[Feature[Geometry, PhysicalObject]],
    status_code=status.HTTP_200_OK,
)
async def get_physical_objects_geojson_by_territory_id(
    request: Request,
    territory_id: int = Path(..., description="territory identifier", gt=0),
    physical_object_type_id: int | None = Query(None, description="to filter by physical object type", gt=0),
    physical_object_function_id: int | None = Query(None, description="to filter by physical object function", gt=0),
    name: str | None = Query(None, description="filter physical objects by name substring (case-insensitive)"),
    include_child_territories: bool = Query(
        True, description="to get from child territories (unsafe for high level territories)"
    ),
    cities_only: bool = Query(False, description="to get only for cities"),
    centers_only: bool = Query(False, description="to get only center points of geometries"),
) -> GeoJSONResponse[Feature[Geometry, PhysicalObject]]:
    """
    ## Get physical objects in GeoJSON format for a given territory.

    **WARNING 1:** Set `cities_only = True` only if you want to get entities from child territories.

    **WARNING 2:** You can only filter by physical object type or physical object function.

    ### Parameters:
    - **territory_id** (int, Path): Unique identifier of the territory.
    - **physical_object_type_id** (int | None, Query): Filters results by physical object type.
    - **physical_object_function_id** (int | None, Query): Filters results by physical object function.
    - **name** (str | None, Query): Filters results by a case-insensitive substring match.
    - **include_child_territories** (bool, Query): If True, includes data from child territories (default: True).
      Note: This can be unsafe for high-level territories due to potential performance issues.
    - **cities_only** (bool, Query): If True, retrieves data only for cities (default: false).
    - **centers_only** (bool, Query): If True, returns only center points of geometries (default: false).

    ### Returns:
    - **GeoJSONResponse[Feature[Geometry, PhysicalObject]]**: A GeoJSON response containing physical objects and their geometries.

    ### Errors:
    - **400 Bad Request**: If `cities_only` is set to True and `include_child_territories` is set to False or
    set both `physical_object_type_id` and `physical_object_function_id`.
    - **404 Not Found**: If the territory does not exist.
    """
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр cities_only можно использовать только при включении дочерних территорий.",
        )

    if physical_object_type_id is not None and physical_object_function_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id.",
        )

    physical_objects = await territories_service.get_physical_objects_with_geometry_by_territory_id(
        territory_id,
        physical_object_type_id,
        physical_object_function_id,
        name,
        include_child_territories,
        cities_only,
        None,
        "asc",
        paginate=False,
    )

    return await GeoJSONResponse.from_list((obj.to_geojson_dict() for obj in physical_objects), centers_only)
