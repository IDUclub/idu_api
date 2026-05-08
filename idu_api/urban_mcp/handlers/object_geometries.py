"""MCP tools for object geometries are defined here."""

from typing import Annotated, Optional

from fastmcp import Context
from fastmcp.dependencies import CurrentRequest, Depends
from fastmcp.server.dependencies import CurrentContext
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.object_geometries import ObjectGeometriesService
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.schemas import (
    ObjectGeometry,
    PhysicalObject,
    ScenarioAllObjects,
    ScenarioGeometryAttributes,
)
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import object_geometries_mcp


def _parse_object_geometries_ids(object_geometries_ids: str) -> set[int]:
    try:
        return {int(geometry.strip()) for geometry in object_geometries_ids.split(",")}
    except ValueError as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр object_geometries_ids должен быть строкой с целочисленными идентификаторами, разделенными запятыми.",
            )
        ) from exc


def _get_scenario_id(context: Context) -> int:
    try:
        return int(context.request_context.meta.scenario_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный scenario_id.",
            )
        ) from exc


@object_geometries_mcp.tool(
    name="GetObjectGeometriesByIds",
    title="Получить геометрии объектов по идентификаторам",
    description="""Возвращает геометрии городских объектов по списку идентификаторов object_geometry_id.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    object_geometries_ids | str | да | Список идентификаторов геометрий объектов через запятую, например "1,2,3".
    
    Выходные данные:
    list[ObjectGeometry] | Список геометрий объектов с территорией, адресом, OSM ID, геометрией и центром.
    
    Поля модели:
    ObjectGeometry:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория, в которой расположена геометрия.
    address | str | None | Адрес объекта, если он задан.
    osm_id | str | None | Идентификатор объекта в OpenStreetMap, если он известен.
    geometry | Geometry | Геометрия объекта.
    centre_point | Point | Центр геометрии объекта.
    created_at | datetime | Дата и время создания геометрии.
    updated_at | datetime | Дата и время последнего обновления геометрии.
    
    Пример вызова:
    {
      "tool": "GetObjectGeometriesByIds",
      "arguments": {
        "object_geometries_ids": "1,2"
      }
    }
    
    Пример результата:
    [
      {
        "object_geometry_id": 1,
        "territory": {"id": 10, "name": "Пермь"},
        "address": "ул. Ленина, 1",
        "osm_id": "123456",
        "geometry": {"type": "Point", "coordinates": [56.25, 58.01]},
        "centre_point": {"type": "Point", "coordinates": [56.25, 58.01]},
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: object_geometries_ids содержит нецелочисленное значение.
    - -32001 Not found: одна или несколько геометрий объектов не найдены.
    """,
    tags=["object_geometries"],
    annotations={"title": "GetObjectGeometriesByIds", "readOnlyHint": True},
)
async def get_object_geometries_by_ids(
    object_geometries_ids: Annotated[str, "Список идентификаторов геометрий через запятую"],
    request: Request = CurrentRequest(),
) -> list[ObjectGeometry]:
    """Get object geometries by identifiers."""
    object_geometries_service: ObjectGeometriesService = request.state.object_geometries_service
    parsed_ids = _parse_object_geometries_ids(object_geometries_ids)
    object_geometries = await object_geometries_service.get_object_geometry_by_ids(parsed_ids)
    return [ObjectGeometry.from_dto(object_geometry) for object_geometry in object_geometries]


@object_geometries_mcp.tool(
    name="GetPhysicalObjectsByGeometryId",
    title="Получить физические объекты по геометрии",
    description="""Возвращает физические объекты, связанные с указанной геометрией объекта.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    object_geometry_id | int | да | Идентификатор геометрии объекта, для которой нужно получить связанные физические объекты.
    
    Выходные данные:
    list[PhysicalObject] | Список физических объектов, размещенных на указанной геометрии.
    
    Поля модели:
    PhysicalObject:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта.
    name | str | None | Название физического объекта, если оно задано.
    properties | dict | Дополнительные свойства физического объекта.
    building | ShortBuilding | None | Связанное здание, если объект расположен в здании.
    territories | list[ShortTerritory] | None | Территории, к которым относится объект.
    created_at | datetime | Дата и время создания физического объекта.
    updated_at | datetime | Дата и время последнего обновления физического объекта.
    
    Пример вызова:
    {
      "tool": "GetPhysicalObjectsByGeometryId",
      "arguments": {
        "object_geometry_id": 1
      }
    }
    
    Пример результата:
    [
      {
        "physical_object_id": 25,
        "physical_object_type": {"physical_object_type_id": 4, "name": "Школа", "physical_object_function": {"id": 2, "name": "Образование"}},
        "name": "Школа N 1",
        "properties": {},
        "building": null,
        "territories": [{"id": 10, "name": "Пермь"}],
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32001 Not found: геометрия объекта не найдена или с ней не связаны физические объекты.
    """,
    tags=["object_geometries", "physical_objects"],
    annotations={"title": "GetPhysicalObjectsByGeometryId", "readOnlyHint": True},
)
async def get_physical_objects_by_geometry_id(
    object_geometry_id: Annotated[int, "Идентификатор геометрии объекта"],
    request: Request = CurrentRequest(),
) -> list[PhysicalObject]:
    """Get physical objects associated with object geometry."""
    object_geometries_service: ObjectGeometriesService = request.state.object_geometries_service
    physical_objects = await object_geometries_service.get_physical_objects_by_object_geometry_id(object_geometry_id)
    return [PhysicalObject.from_dto(physical_object) for physical_object in physical_objects]


@object_geometries_mcp.tool(
    name="GetScenarioGeometries",
    title="Получить геометрии сценария",
    description="""Возвращает геометрии объектов проектной территории текущего сценария в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | Optional[int] | нет | Фильтр по идентификатору физического объекта сценария или базового объекта.
    service_id | Optional[int] | нет | Фильтр по идентификатору сервиса сценария или базового сервиса.
    centers_only | bool | нет | Если true, вместо полной геометрии возвращается центр геометрии.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioGeometryAttributes]] | GeoJSON FeatureCollection с геометриями объектов сценария и атрибутами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioGeometryAttributes:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория, в которой расположена геометрия.
    address | str | None | Адрес объекта, если он задан.
    osm_id | str | None | Идентификатор объекта в OpenStreetMap, если он известен.
    created_at | datetime | Дата и время создания геометрии.
    updated_at | datetime | Дата и время последнего обновления геометрии.
    is_scenario_object | bool | Признак того, что геометрия создана или изменена в сценарии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {
      "tool": "GetScenarioGeometries",
      "arguments": {
        "physical_object_id": 1,
        "service_id": 1,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [30.0, 60.0]},
          "properties": {
            "object_geometry_id": 1,
            "territory": {"id": 10, "name": "Пермь"},
            "address": "ул. Ленина, 1",
            "osm_id": "123456",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "is_scenario_object": true,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, физический объект или сервис не найдены.
    """,
    tags=["object_geometries", "scenarios"],
    annotations={"title": "GetScenarioGeometries", "readOnlyHint": True},
)
async def get_geometries_by_scenario_id(
    physical_object_id: Annotated[Optional[int], "Фильтр по физическому объекту"] = None,
    service_id: Annotated[Optional[int], "Фильтр по сервису"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioGeometryAttributes]]:
    """Get geometries for the current scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)

    geometries = await user_project_service.get_geometries_by_scenario_id(
        scenario_id,
        user,
        physical_object_id,
        service_id,
    )

    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in geometries], centers_only)


@object_geometries_mcp.tool(
    name="GetScenarioGeometriesWithAllObjects",
    title="Получить геометрии сценария со всеми объектами",
    description="""Возвращает геометрии текущего сценария вместе со всеми связанными физическими объектами и сервисами в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id и exclude_physical_object_function_id.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id и exclude_urban_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции сервиса.
    exclude_physical_object_function_id | Optional[int] | нет | Исключает физические объекты с указанной функцией.
    exclude_urban_function_id | Optional[int] | нет | Исключает сервисы с указанной городской функцией.
    centers_only | bool | нет | Если true, вместо полной геометрии возвращается центр геометрии.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioAllObjects]] | GeoJSON FeatureCollection с геометриями, физическими объектами и сервисами сценария в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioAllObjects:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория, в которой расположена геометрия.
    address | str | None | Адрес объекта, если он задан.
    osm_id | str | None | Идентификатор объекта в OpenStreetMap, если он известен.
    physical_objects | list | Связанные физические объекты, включая признак сценарного объекта.
    services | list | Связанные сервисы, включая признак сценарного объекта.
    is_scenario_object | bool | Признак того, что геометрия создана или изменена в сценарии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {
      "tool": "GetScenarioGeometriesWithAllObjects",
      "arguments": {
        "physical_object_type_id": 1,
        "service_type_id": 5,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [30.0, 60.0]},
          "properties": {
            "object_geometry_id": 1,
            "territory": {"id": 10, "name": "Пермь"},
            "address": "ул. Ленина, 1",
            "osm_id": "123456",
            "physical_objects": [{"physical_object_id": 25, "name": "Школа N 1", "is_scenario_object": true}],
            "services": [{"service_id": 30, "name": "Образовательная услуга", "is_scenario_object": true}],
            "is_scenario_object": true,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: physical_object_type_id нельзя использовать одновременно с physical_object_function_id или exclude_physical_object_function_id.
    - -32602 Invalid params: service_type_id нельзя использовать одновременно с urban_function_id или exclude_urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, тип объекта, функция объекта, тип сервиса или городская функция не найдены.
    """,
    tags=["object_geometries", "scenarios"],
    annotations={"title": "GetScenarioGeometriesWithAllObjects", "readOnlyHint": True},
)
async def get_geometries_with_all_objects_by_scenario_id(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    urban_function_id: Annotated[Optional[int], "Фильтр по городской функции"] = None,
    exclude_physical_object_function_id: Annotated[Optional[int], "Исключить функцию физического объекта"] = None,
    exclude_urban_function_id: Annotated[Optional[int], "Исключить городскую функцию"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioAllObjects]]:
    """Get scenario geometries with all related objects in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)

    if physical_object_type_id is not None and (
        physical_object_function_id is not None or exclude_physical_object_function_id is not None
    ):
        raise McpError(
            ErrorData(
                code=-32602,
                message="Фильтр physical_object_type_id нельзя использовать одновременно с physical_object_function_id или exclude_physical_object_function_id.",
            )
        )

    if service_type_id is not None and (urban_function_id is not None or exclude_urban_function_id is not None):
        raise McpError(
            ErrorData(
                code=-32602,
                message="Фильтр service_type_id нельзя использовать одновременно с urban_function_id или exclude_urban_function_id.",
            )
        )

    geometries = await user_project_service.get_geometries_with_all_objects_by_scenario_id(
        scenario_id,
        user,
        physical_object_type_id,
        service_type_id,
        physical_object_function_id,
        urban_function_id,
        exclude_physical_object_function_id,
        exclude_urban_function_id,
    )

    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in geometries], centers_only)


@object_geometries_mcp.tool(
    name="GetContextGeometries",
    title="Получить геометрии контекста",
    description="""Возвращает геометрии контекста текущего сценария в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | Optional[int] | нет | Фильтр по идентификатору физического объекта контекста.
    service_id | Optional[int] | нет | Фильтр по идентификатору сервиса контекста.
    centers_only | bool | нет | Если true, вместо полной геометрии возвращается центр геометрии.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioGeometryAttributes]] | GeoJSON FeatureCollection с контекстными геометриями и атрибутами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioGeometryAttributes:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория, в которой расположена геометрия.
    address | str | None | Адрес объекта, если он задан.
    osm_id | str | None | Идентификатор объекта в OpenStreetMap, если он известен.
    created_at | datetime | Дата и время создания геометрии.
    updated_at | datetime | Дата и время последнего обновления геометрии.
    is_scenario_object | bool | Признак того, что геометрия относится к объектам сценария.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {
      "tool": "GetContextGeometries",
      "arguments": {
        "physical_object_id": 1,
        "service_id": 1,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [30.0, 60.0]},
          "properties": {
            "object_geometry_id": 1,
            "territory": {"id": 10, "name": "Пермь"},
            "address": "ул. Ленина, 1",
            "osm_id": "123456",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "is_scenario_object": false,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, физический объект или сервис контекста не найдены.
    """,
    tags=["object_geometries", "scenarios", "context"],
    annotations={"title": "GetContextGeometries", "readOnlyHint": True},
)
async def get_context_geometries(
    physical_object_id: Annotated[Optional[int], "Фильтр по физическому объекту"] = None,
    service_id: Annotated[Optional[int], "Фильтр по сервису"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioGeometryAttributes]]:
    """Get context geometries for the current scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)

    geometries = await user_project_service.get_context_geometries(
        scenario_id,
        user,
        physical_object_id,
        service_id,
    )

    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in geometries], centers_only)


@object_geometries_mcp.tool(
    name="GetContextGeometriesWithAllObjects",
    title="Получить геометрии контекста со всеми объектами",
    description="""Возвращает геометрии контекста текущего сценария вместе со связанными физическими объектами и сервисами в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id и exclude_physical_object_function_id.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id и exclude_urban_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции сервиса.
    exclude_physical_object_function_id | Optional[int] | нет | Исключает физические объекты с указанной функцией.
    exclude_urban_function_id | Optional[int] | нет | Исключает сервисы с указанной городской функцией.
    include_scenario_objects | bool | нет | Если true, вместе с контекстом в ответ включаются объекты текущего сценария.
    centers_only | bool | нет | Если true, вместо полной геометрии возвращается центр геометрии.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioAllObjects]] | GeoJSON FeatureCollection с контекстными геометриями, физическими объектами и сервисами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioAllObjects:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория, в которой расположена геометрия.
    address | str | None | Адрес объекта, если он задан.
    osm_id | str | None | Идентификатор объекта в OpenStreetMap, если он известен.
    physical_objects | list | Связанные физические объекты с признаком сценарного объекта.
    services | list | Связанные сервисы с признаком сценарного объекта.
    is_scenario_object | bool | Признак того, что геометрия относится к объектам сценария.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {
      "tool": "GetContextGeometriesWithAllObjects",
      "arguments": {
        "physical_object_type_id": 1,
        "service_type_id": 5,
        "include_scenario_objects": true,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [30.0, 60.0]},
          "properties": {
            "object_geometry_id": 1,
            "territory": {"id": 10, "name": "Пермь"},
            "address": "ул. Ленина, 1",
            "osm_id": "123456",
            "physical_objects": [{"physical_object_id": 25, "name": "Школа N 1", "is_scenario_object": false}],
            "services": [{"service_id": 30, "name": "Образовательная услуга", "is_scenario_object": false}],
            "is_scenario_object": false,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: physical_object_type_id нельзя использовать одновременно с physical_object_function_id или exclude_physical_object_function_id.
    - -32602 Invalid params: service_type_id нельзя использовать одновременно с urban_function_id или exclude_urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, тип объекта, функция объекта, тип сервиса или городская функция не найдены.
    """,
    tags=["object_geometries", "scenarios", "context"],
    annotations={"title": "GetContextGeometriesWithAllObjects", "readOnlyHint": True},
)
async def get_context_geometries_with_all_objects(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    urban_function_id: Annotated[Optional[int], "Фильтр по городской функции"] = None,
    exclude_physical_object_function_id: Annotated[Optional[int], "Исключить функцию физического объекта"] = None,
    exclude_urban_function_id: Annotated[Optional[int], "Исключить городскую функцию"] = None,
    include_scenario_objects: Annotated[bool, "Включать объекты сценария в контекст"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioAllObjects]]:
    """Get context geometries with all related objects in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)

    if physical_object_type_id is not None and (
        physical_object_function_id is not None or exclude_physical_object_function_id is not None
    ):
        raise McpError(
            ErrorData(
                code=-32602,
                message="Фильтр physical_object_type_id нельзя использовать одновременно с physical_object_function_id или exclude_physical_object_function_id.",
            )
        )

    if service_type_id is not None and (urban_function_id is not None or exclude_urban_function_id is not None):
        raise McpError(
            ErrorData(
                code=-32602,
                message="Фильтр service_type_id нельзя использовать одновременно с urban_function_id или exclude_urban_function_id.",
            )
        )

    geometries = await user_project_service.get_context_geometries_with_all_objects(
        scenario_id,
        user,
        physical_object_type_id,
        service_type_id,
        physical_object_function_id,
        urban_function_id,
        exclude_physical_object_function_id,
        exclude_urban_function_id,
        include_scenario_objects,
    )

    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in geometries], centers_only)
