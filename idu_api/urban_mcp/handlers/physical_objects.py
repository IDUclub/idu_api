"""MCP tools for physical objects are defined here."""

from typing import Annotated, Optional

from fastmcp import Context
from fastmcp.dependencies import CurrentRequest, Depends
from fastmcp.server.dependencies import CurrentContext
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.physical_object_types import PhysicalObjectTypesService
from idu_api.urban_api.logic.physical_objects import PhysicalObjectsService
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    ObjectGeometry,
    PhysicalObject,
    PhysicalObjectFunction,
    PhysicalObjectsTypesHierarchy,
    PhysicalObjectType,
    ScenarioPhysicalObject,
    ScenarioPhysicalObjectWithGeometryAttributes,
    Service,
    ServiceType,
    ServiceWithGeometry,
)
from idu_api.urban_api.schemas.enums import OrderByField, Ordering
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_api.schemas.pages import MCPCursorPage, MCPCursorParams
from idu_api.urban_api.schemas.physical_objects import PhysicalObjectWithGeometry
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import physical_objects_mcp


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


def _parse_ids(ids: str | None) -> set[int] | None:
    if ids is None:
        return None
    try:
        return {int(type_id.strip()) for type_id in ids.split(",")}
    except ValueError as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр ids должен быть строкой с целочисленными идентификаторами, разделенными запятыми.",
            )
        ) from exc


def _validate_child_territories(include_child_territories: bool, cities_only: bool) -> None:
    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )


def _validate_type_or_function(physical_object_type_id: int | None, physical_object_function_id: int | None) -> None:
    if physical_object_type_id is not None and physical_object_function_id is not None:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Укажите только один фильтр: physical_object_type_id или physical_object_function_id.",
            )
        )


@physical_objects_mcp.tool(
    name="GetPhysicalObjectTypes",
    title="Получить типы физических объектов",
    description="""Возвращает типы физических объектов с фильтрами по функции физического объекта и названию.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_function_id | Optional[int] | нет | Фильтр по идентификатору функции физического объекта.
    name | Optional[str] | нет | Фильтр по подстроке в названии типа без учета регистра.
    
    Выходные данные:
    list[PhysicalObjectType] | Список типов физических объектов.
    
    Поля модели:
    PhysicalObjectType:
    Поле | Тип | Описание
    physical_object_type_id | int | Идентификатор типа физического объекта.
    name | str | Название типа физического объекта.
    physical_object_function | PhysicalObjectFunctionBasic | Функция, к которой относится тип.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectTypes", "arguments": {"physical_object_function_id": 2, "name": "школа"}}
    
    Пример результата:
    [{"physical_object_type_id": 4, "name": "Школа", "physical_object_function": {"id": 2, "name": "Образование"}}]
    
    Ошибки:
    - -32001 Not found: функция физического объекта не найдена или по фильтрам нет доступных типов.
    """,
    tags=["physical_objects"],
    annotations={"title": "GetPhysicalObjectTypes", "readOnlyHint": True},
)
async def get_physical_object_types(
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    name: Annotated[Optional[str], "Фильтр по названию"] = None,
    request: Request = CurrentRequest(),
) -> list[PhysicalObjectType]:
    """Get physical object types."""
    physical_object_types_service: PhysicalObjectTypesService = request.state.physical_object_types_service
    types = await physical_object_types_service.get_physical_object_types(physical_object_function_id, name)
    return [PhysicalObjectType.from_dto(object_type) for object_type in types]


@physical_objects_mcp.tool(
    name="GetPhysicalObjectFunctionsByParent",
    title="Получить функции физических объектов по родителю",
    description="""Возвращает функции физических объектов из иерархии по родительской функции и фильтру названия.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской функции; если не указан, возвращаются функции верхнего уровня.
    name | Optional[str] | нет | Фильтр по подстроке в названии функции без учета регистра.
    get_all_subtree | bool | нет | Если true, возвращается все поддерево родительской функции.
    
    Выходные данные:
    list[PhysicalObjectFunction] | Список функций физических объектов.
    
    Поля модели:
    PhysicalObjectFunction:
    Поле | Тип | Описание
    physical_object_function_id | int | Идентификатор функции физического объекта.
    parent_physical_object_function | PhysicalObjectFunctionBasic | None | Родительская функция, если она есть.
    name | str | Название функции физического объекта.
    level | int | Уровень функции в иерархии.
    list_label | str | Маркер функции в иерархическом списке.
    code | str | Код функции.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectFunctionsByParent", "arguments": {"parent_id": 1, "name": "образ", "get_all_subtree": false}}
    
    Пример результата:
    [{"physical_object_function_id": 2, "parent_physical_object_function": {"id": 1, "name": "Социальные объекты"}, "name": "Образование", "level": 2, "list_label": "1.1", "code": "EDU"}]

    Ошибки:
    - -32001 Not found: родительская функция физического объекта не найдена.
    """,
    tags=["physical_objects"],
    annotations={"title": "GetPhysicalObjectFunctionsByParent", "readOnlyHint": True},
)
async def get_physical_object_functions_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по названию функции"] = None,
    get_all_subtree: Annotated[bool, "Вернуть всё поддерево"] = False,
    request: Request = CurrentRequest(),
) -> list[PhysicalObjectFunction]:
    """Get physical object functions by parent identifier."""
    physical_object_types_service: PhysicalObjectTypesService = request.state.physical_object_types_service
    functions = await physical_object_types_service.get_physical_object_functions_by_parent_id(
        parent_id, name, get_all_subtree
    )
    return [PhysicalObjectFunction.from_dto(item) for item in functions]


@physical_objects_mcp.tool(
    name="GetPhysicalObjectTypesHierarchy",
    title="Получить иерархию типов физических объектов",
    description="""Возвращает иерархию функций физических объектов с вложенными типами физических объектов.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_types_ids | Optional[str] | нет | Список идентификаторов типов физических объектов через запятую; если указан, дерево ограничивается этими типами.
    
    Выходные данные:
    list[PhysicalObjectsTypesHierarchy] | Дерево функций физических объектов и вложенных типов.
    
    Поля модели:
    PhysicalObjectsTypesHierarchy:
    Поле | Тип | Описание
    physical_object_function_id | int | Идентификатор функции физического объекта.
    parent_id | int | None | Идентификатор родительской функции.
    name | str | Название функции.
    level | int | Уровень функции в дереве.
    list_label | str | Маркер функции в иерархическом списке.
    code | str | Код функции.
    children | list | Дочерние функции или типы физических объектов.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectTypesHierarchy", "arguments": {"physical_object_types_ids": "4,5"}}
    
    Пример результата:
    [{"physical_object_function_id": 2, "parent_id": 1, "name": "Образование", "level": 2, "list_label": "1.1", "code": "EDU", "children": [{"physical_object_type_id": 4, "name": "Школа"}]}]
    
    Ошибки:
    - -32602 Invalid params: physical_object_types_ids содержит нецелочисленное значение.
    - -32001 Not found: один из типов физических объектов не найден.
    """,
    tags=["physical_objects"],
    annotations={"title": "GetPhysicalObjectTypesHierarchy", "readOnlyHint": True},
)
async def get_physical_object_types_hierarchy(
    physical_object_types_ids: Annotated[Optional[str], "Список идентификаторов типов через запятую"] = None,
    request: Request = CurrentRequest(),
) -> list[PhysicalObjectsTypesHierarchy]:
    """Get hierarchy of physical object types."""
    physical_object_types_service: PhysicalObjectTypesService = request.state.physical_object_types_service
    ids = _parse_ids(physical_object_types_ids)
    hierarchy = await physical_object_types_service.get_physical_object_types_hierarchy(ids)
    return [PhysicalObjectsTypesHierarchy.from_dto(node) for node in hierarchy]


@physical_objects_mcp.tool(
    name="GetServiceTypesByPhysicalObjectType",
    title="Получить типы сервисов по типу физического объекта",
    description="""Возвращает типы сервисов, которые могут быть размещены в указанном типе физического объекта.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | int | да | Идентификатор типа физического объекта.
    
    Выходные данные:
    list[ServiceType] | Список типов сервисов, связанных с типом физического объекта.
    
    Поля модели:
    ServiceType:
    Поле | Тип | Описание
    service_type_id | int | Идентификатор типа сервиса.
    urban_function | UrbanFunctionBasic | Городская функция сервиса.
    name | str | Название типа сервиса.
    capacity_modeled | int | None | Модельная мощность по умолчанию.
    code | str | Код типа сервиса.
    infrastructure_type | Optional | Тип инфраструктуры.
    properties | dict | Дополнительные свойства типа сервиса.
    
    Пример вызова:
    {"tool": "GetServiceTypesByPhysicalObjectType", "arguments": {"physical_object_type_id": 4}}
    
    Пример результата:
    [{"service_type_id": 7, "urban_function": {"id": 2, "name": "Образование"}, "name": "Школьное образование", "capacity_modeled": 500, "code": "school", "infrastructure_type": "basic", "properties": {}}]
    
    Ошибки:
    - -32001 Not found: тип физического объекта не найден.
    """,
    tags=["physical_objects", "services"],
    annotations={"title": "GetServiceTypesByPhysicalObjectType", "readOnlyHint": True},
)
async def get_service_types(
    physical_object_type_id: Annotated[int, "Идентификатор типа физического объекта"],
    request: Request = CurrentRequest(),
) -> list[ServiceType]:
    """Get service types by physical object type."""
    physical_object_types_service: PhysicalObjectTypesService = request.state.physical_object_types_service
    service_types = await physical_object_types_service.get_service_types_by_physical_object_type(
        physical_object_type_id
    )
    return [ServiceType.from_dto(service_type) for service_type in service_types]


@physical_objects_mcp.tool(
    name="GetPhysicalObjectById",
    title="Получить физический объект по идентификатору",
    description="""Возвращает полную карточку физического объекта по его идентификатору.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | int | да | Идентификатор физического объекта.
    
    Выходные данные:
    PhysicalObject | Карточка физического объекта.
    
    Поля модели:
    PhysicalObject:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта, если оно задано.
    properties | dict | Дополнительные свойства физического объекта.
    building | ShortBuilding | None | Связанное здание, если объект расположен в здании.
    territories | list[ShortTerritory] | None | Территории, к которым относится объект.
    created_at | datetime | Дата и время создания объекта.
    updated_at | datetime | Дата и время последнего обновления объекта.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectById", "arguments": {"physical_object_id": 25}}
    
    Пример результата:
    {"physical_object_id": 25, "physical_object_type": {"physical_object_type_id": 4, "name": "Школа"}, "name": "Школа N 1", "properties": {}, "building": null, "territories": [{"id": 10, "name": "Пермь"}], "created_at": "2024-01-15T10:00:00Z", "updated_at": "2024-01-15T10:00:00Z"}
    
    Ошибки:
    - -32001 Not found: физический объект с указанным physical_object_id не найден.
    """,
    tags=["physical_objects"],
    annotations={"title": "GetPhysicalObjectById", "readOnlyHint": True},
)
async def get_physical_object_by_id(
    physical_object_id: Annotated[int, "Идентификатор физического объекта"],
    request: Request = CurrentRequest(),
) -> PhysicalObject:
    """Get physical object by identifier."""
    physical_objects_service: PhysicalObjectsService = request.state.physical_objects_service
    physical_object = await physical_objects_service.get_physical_object_by_id(physical_object_id)
    return PhysicalObject.from_dto(physical_object)


@physical_objects_mcp.tool(
    name="GetServicesByPhysicalObjectId",
    title="Получить сервисы по физическому объекту",
    description="""Возвращает сервисы, связанные с указанным физическим объектом, с фильтрами по типу сервиса и типу территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | int | да | Идентификатор физического объекта.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории обслуживания.
    
    Выходные данные:
    list[Service] | Список сервисов физического объекта.
    
    Поля модели:
    Service:
    Поле | Тип | Описание
    service_id | int | Идентификатор сервиса.
    service_type | ServiceType | Тип сервиса.
    territory_type | TerritoryType | None | Тип территории обслуживания.
    name | str | None | Название сервиса.
    capacity | int | None | Мощность сервиса.
    is_capacity_real | bool | None | Признак фактической мощности.
    territories | list[ShortTerritory] | None | Территории обслуживания.
    properties | dict | Дополнительные свойства сервиса.
    created_at | datetime | Дата и время создания сервиса.
    updated_at | datetime | Дата и время последнего обновления сервиса.
    
    Пример вызова:
    {"tool": "GetServicesByPhysicalObjectId", "arguments": {"physical_object_id": 25, "service_type_id": 7, "territory_type_id": 1}}
    
    Пример результата:
    [{"service_id": 30, "service_type": {"service_type_id": 7, "name": "Школьное образование"}, "territory_type": {"territory_type_id": 1, "name": "Город"}, "name": "Школьное образование", "capacity": 500, "is_capacity_real": true, "territories": [{"id": 10, "name": "Пермь"}], "properties": {}, "created_at": "2024-01-15T10:00:00Z", "updated_at": "2024-01-15T10:00:00Z"}]
    
    Ошибки:
    - -32001 Not found: физический объект, тип сервиса или тип территории не найдены.
    """,
    tags=["physical_objects", "services"],
    annotations={"title": "GetServicesByPhysicalObjectId", "readOnlyHint": True},
)
async def get_services_by_physical_object_id(
    physical_object_id: Annotated[int, "Идентификатор физического объекта"],
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    request: Request = CurrentRequest(),
) -> list[Service]:
    """Get services by physical object identifier."""
    physical_objects_service: PhysicalObjectsService = request.state.physical_objects_service
    services = await physical_objects_service.get_services_by_physical_object_id(
        physical_object_id, service_type_id, territory_type_id
    )
    return [Service.from_dto(service) for service in services]


@physical_objects_mcp.tool(
    name="GetServicesWithGeometryByPhysicalObjectId",
    title="Получить сервисы с геометрией по физическому объекту",
    description="""Возвращает сервисы указанного физического объекта вместе с геометрией размещения.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | int | да | Идентификатор физического объекта.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории обслуживания.
    
    Выходные данные:
    list[ServiceWithGeometry] | Список сервисов с геометрией объекта.
    
    Поля модели:
    ServiceWithGeometry:
    Поле | Тип | Описание
    service_id | int | Идентификатор сервиса.
    service_type | ServiceType | Тип сервиса.
    territory_type | TerritoryType | None | Тип территории обслуживания.
    territory | ShortTerritory | Территория размещения геометрии.
    name | str | None | Название сервиса.
    capacity | int | None | Мощность сервиса.
    is_capacity_real | bool | None | Признак фактической мощности.
    properties | dict | Дополнительные свойства сервиса.
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    geometry | Geometry | Геометрия объекта.
    centre_point | Point | Центр геометрии.
    
    Пример вызова:
    {"tool": "GetServicesWithGeometryByPhysicalObjectId", "arguments": {"physical_object_id": 25, "service_type_id": 7}}
    
    Пример результата:
    [{"service_id": 30, "service_type": {"service_type_id": 7, "name": "Школьное образование"}, "territory": {"id": 10, "name": "Пермь"}, "name": "Школьное образование", "capacity": 500, "object_geometry_id": 100, "address": "ул. Ленина, 1", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}}]
    
    Ошибки:
    - -32001 Not found: физический объект, тип сервиса, тип территории или геометрия не найдены.
    """,
    tags=["physical_objects", "services"],
    annotations={"title": "GetServicesWithGeometryByPhysicalObjectId", "readOnlyHint": True},
)
async def get_services_with_geometry_by_physical_object_id(
    physical_object_id: Annotated[int, "Идентификатор физического объекта"],
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    request: Request = CurrentRequest(),
) -> list[ServiceWithGeometry]:
    """Get services with geometry by physical object identifier."""
    physical_objects_service: PhysicalObjectsService = request.state.physical_objects_service
    services = await physical_objects_service.get_services_with_geometry_by_physical_object_id(
        physical_object_id, service_type_id, territory_type_id
    )
    return [ServiceWithGeometry.from_dto(service) for service in services]


@physical_objects_mcp.tool(
    name="GetPhysicalObjectGeometries",
    title="Получить геометрии физического объекта",
    description="""Возвращает геометрии, связанные с указанным физическим объектом.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | int | да | Идентификатор физического объекта.
    
    Выходные данные:
    list[ObjectGeometry] | Список геометрий физического объекта.
    
    Поля модели:
    ObjectGeometry:
    Поле | Тип | Описание
    object_geometry_id | int | Идентификатор геометрии объекта.
    territory | ShortTerritory | Территория размещения геометрии.
    address | str | None | Адрес объекта.
    osm_id | str | None | Идентификатор OpenStreetMap.
    geometry | Geometry | Геометрия объекта.
    centre_point | Point | Центр геометрии.
    created_at | datetime | Дата и время создания геометрии.
    updated_at | datetime | Дата и время последнего обновления геометрии.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectGeometries", "arguments": {"physical_object_id": 25}}
    
    Пример результата:
    [{"object_geometry_id": 100, "territory": {"id": 10, "name": "Пермь"}, "address": "ул. Ленина, 1", "osm_id": "123456", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "centre_point": {"type": "Point", "coordinates": [56.25, 58.01]}, "created_at": "2024-01-15T10:00:00Z", "updated_at": "2024-01-15T10:00:00Z"}]
    
    Ошибки:
    - -32001 Not found: физический объект не найден или у него нет геометрий.
    """,
    tags=["physical_objects", "object_geometries"],
    annotations={"title": "GetPhysicalObjectGeometries", "readOnlyHint": True},
)
async def get_physical_object_geometries(
    physical_object_id: Annotated[int, "Идентификатор физического объекта"],
    request: Request = CurrentRequest(),
) -> list[ObjectGeometry]:
    """Get geometries of physical object."""
    physical_objects_service: PhysicalObjectsService = request.state.physical_objects_service
    geometries = await physical_objects_service.get_physical_object_geometries(physical_object_id)
    return [ObjectGeometry.from_dto(geometry) for geometry in geometries]


@physical_objects_mcp.tool(
    name="GetPhysicalObjectTypesByTerritoryId",
    title="Получить типы физических объектов территории",
    description="""Возвращает типы физических объектов, представленные на указанной территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    list[PhysicalObjectType] | Список типов физических объектов территории.
    
    Поля модели:
    PhysicalObjectType:
    Поле | Тип | Описание
    physical_object_type_id | int | Идентификатор типа физического объекта.
    name | str | Название типа физического объекта.
    physical_object_function | PhysicalObjectFunctionBasic | Функция, к которой относится тип.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectTypesByTerritoryId", "arguments": {"territory_id": 10, "include_child_territories": true, "cities_only": false}}
    
    Пример результата:
    [{"physical_object_type_id": 4, "name": "Школа", "physical_object_function": {"id": 2, "name": "Образование"}}]
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория не найдена.
    """,
    tags=["physical_objects", "territories"],
    annotations={"title": "GetPhysicalObjectTypesByTerritoryId", "readOnlyHint": True},
)
async def get_physical_object_types_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    request: Request = CurrentRequest(),
) -> list[PhysicalObjectType]:
    """Get physical object types for territory."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    physical_object_types = await territories_service.get_physical_object_types_by_territory_id(
        territory_id, include_child_territories, cities_only
    )
    return [PhysicalObjectType.from_dto(service_type) for service_type in physical_object_types]


@physical_objects_mcp.tool(
    name="GetTerritoryPhysicalObjectsGeoJSON",
    title="Получить физические объекты территории в GeoJSON",
    description="""Возвращает физические объекты территории в формате GeoJSON с возможностью вернуть центры вместо геометрии.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    name | Optional[str] | нет | Фильтр по подстроке в названии.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, PhysicalObjectWithGeometry]] | GeoJSON FeatureCollection с объектами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список Feature с geometry и properties.
    PhysicalObjectWithGeometry:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    territory | ShortTerritory | Территория размещения геометрии.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    geometry | Geometry | Геометрия объекта.
    centre_point | Point | Центр геометрии.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    
    Пример вызова:
    {"tool": "GetTerritoryPhysicalObjectsGeoJSON", "arguments": {"territory_id": 10, "physical_object_type_id": 4, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"physical_object_id": 25, "object_geometry_id": 100, "name": "Школа N 1"}}]}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32001 Not found: территория, тип, функция или геометрия объекта не найдены.
    """,
    tags=["physical_objects", "territories"],
    annotations={"title": "GetTerritoryPhysicalObjectsGeoJSON", "readOnlyHint": True},
)
async def get_physical_objects_geojson_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    name: Annotated[Optional[str], "Фильтр по названию"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, PhysicalObject]]:
    """Get territory physical objects in GeoJSON format."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
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


@physical_objects_mcp.tool(
    name="GetScenarioPhysicalObjectTypes",
    title="Получить типы физических объектов сценария",
    description="""Возвращает типы физических объектов, присутствующие в текущем сценарии.
    Входные параметры:
    отсутствуют; идентификатор сценария берется из metadata.scenario_id MCP-запроса.
    
    Выходные данные:
    list[PhysicalObjectType] | Список типов физических объектов сценария.
    
    Поля модели:
    PhysicalObjectType:
    Поле | Тип | Описание
    physical_object_type_id | int | Идентификатор типа физического объекта.
    name | str | Название типа физического объекта.
    physical_object_function | PhysicalObjectFunctionBasic | Функция, к которой относится тип.
    
    Пример вызова:
    {"tool": "GetScenarioPhysicalObjectTypes", "arguments": {}}
    
    Пример результата:
    [{"physical_object_type_id": 4, "name": "Школа", "physical_object_function": {"id": 2, "name": "Образование"}}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий не найден.
    """,
    tags=["physical_objects", "scenarios"],
    annotations={"title": "GetScenarioPhysicalObjectTypes", "readOnlyHint": True},
)
async def get_physical_object_types_by_scenario_id(
    for_context: Annotated[bool, "Вернуть типы для контекста"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[PhysicalObjectType]:
    """Get physical object types for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    types = await user_project_service.get_physical_object_types_by_scenario_id_from_db(scenario_id, user, for_context)
    return [PhysicalObjectType.from_dto(phys_type) for phys_type in types]


@physical_objects_mcp.tool(
    name="GetScenarioPhysicalObjects",
    title="Получить физические объекты сценария",
    description="""Возвращает физические объекты текущего сценария с фильтрами по типу или функции.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ScenarioPhysicalObject] | Список физических объектов сценария.
    
    Поля модели:
    ScenarioPhysicalObject:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    territories | list[ShortTerritory] | None | Территории объекта.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    is_scenario_object | bool | Признак объекта, созданного или измененного в сценарии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {"tool": "GetScenarioPhysicalObjects", "arguments": {"physical_object_type_id": 4}}
    
    Пример результата:
    [{"physical_object_id": 25, "name": "Школа N 1", "is_scenario_object": true, "is_locked": false}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип или функция физического объекта не найдены.
    """,
    tags=["physical_objects", "scenarios"],
    annotations={"title": "GetScenarioPhysicalObjects", "readOnlyHint": True},
)
async def get_physical_objects_by_scenario_id(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ScenarioPhysicalObject]:
    """Get physical objects for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    physical_objects = await user_project_service.get_physical_objects_by_scenario_id(
        scenario_id, user, physical_object_type_id, physical_object_function_id
    )
    return [ScenarioPhysicalObject.from_dto(phys_obj) for phys_obj in physical_objects]


@physical_objects_mcp.tool(
    name="GetScenarioPhysicalObjectsWithGeometry",
    title="Получить физические объекты сценария с геометрией",
    description="""Возвращает физические объекты текущего сценария в формате GeoJSON вместе с геометрией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioPhysicalObjectWithGeometryAttributes]] | GeoJSON FeatureCollection с объектами сценария.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список Feature с geometry и properties.
    ScenarioPhysicalObjectWithGeometryAttributes:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    territories | list[ShortTerritory] | None | Территории объекта.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    is_scenario_physical_object | bool | Признак сценарного физического объекта.
    is_scenario_geometry | bool | Признак сценарной геометрии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {"tool": "GetScenarioPhysicalObjectsWithGeometry", "arguments": {"physical_object_type_id": 4, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"physical_object_id": 25, "object_geometry_id": 100, "is_scenario_physical_object": true, "is_locked": false}}]}
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип, функция или геометрия объекта не найдены.
    """,
    tags=["physical_objects", "scenarios"],
    annotations={"title": "GetScenarioPhysicalObjectsWithGeometry", "readOnlyHint": True},
)
async def get_physical_objects_with_geometry_by_scenario_id(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioPhysicalObjectWithGeometryAttributes]]:
    """Get physical objects with geometry for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    physical_objects = await user_project_service.get_physical_objects_with_geometry_by_scenario_id(
        scenario_id, user, physical_object_type_id, physical_object_function_id
    )
    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in physical_objects], centers_only)


@physical_objects_mcp.tool(
    name="GetContextPhysicalObjects",
    title="Получить физические объекты контекста",
    description="""Возвращает физические объекты контекста текущего сценария с фильтрами по типу или функции.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ScenarioPhysicalObject] | Список контекстных физических объектов.
    
    Поля модели:
    ScenarioPhysicalObject:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    territories | list[ShortTerritory] | None | Территории объекта.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    is_scenario_object | bool | Признак объекта, созданного или измененного в сценарии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {"tool": "GetContextPhysicalObjects", "arguments": {"physical_object_function_id": 2}}
    
    Пример результата:
    [{"physical_object_id": 25, "name": "Школа N 1", "is_scenario_object": false, "is_locked": false}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип или функция физического объекта не найдены.
    """,
    tags=["physical_objects", "scenarios", "context"],
    annotations={"title": "GetContextPhysicalObjects", "readOnlyHint": True},
)
async def get_context_physical_objects(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ScenarioPhysicalObject]:
    """Get context physical objects for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    physical_objects = await user_project_service.get_context_physical_objects(
        scenario_id, user, physical_object_type_id, physical_object_function_id
    )
    return [ScenarioPhysicalObject.from_dto(phys_obj) for phys_obj in physical_objects]


@physical_objects_mcp.tool(
    name="GetContextPhysicalObjectsWithGeometry",
    title="Получить физические объекты контекста с геометрией",
    description="""Возвращает физические объекты контекста текущего сценария в GeoJSON вместе с геометрией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    include_scenario_objects | bool | нет | Если true, вместе с контекстом включаются объекты сценария.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioPhysicalObjectWithGeometryAttributes]] | GeoJSON FeatureCollection с контекстными объектами.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список Feature с geometry и properties.
    ScenarioPhysicalObjectWithGeometryAttributes:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    territories | list[ShortTerritory] | None | Территории объекта.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    is_scenario_physical_object | bool | Признак сценарного физического объекта.
    is_scenario_geometry | bool | Признак сценарной геометрии.
    is_locked | bool | Признак блокировки объекта для редактирования.
    
    Пример вызова:
    {"tool": "GetContextPhysicalObjectsWithGeometry", "arguments": {"physical_object_function_id": 2, "include_scenario_objects": true, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"physical_object_id": 25, "object_geometry_id": 100, "is_scenario_physical_object": false, "is_locked": false}}]}
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип, функция или геометрия объекта не найдены.
    """,
    tags=["physical_objects", "scenarios", "context"],
    annotations={"title": "GetContextPhysicalObjectsWithGeometry", "readOnlyHint": True},
)
async def get_context_physical_objects_with_geometry(
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    include_scenario_objects: Annotated[bool, "Включать объекты сценария в контекст"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioPhysicalObjectWithGeometryAttributes]]:
    """Get context physical objects with geometry for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    physical_objects = await user_project_service.get_context_physical_objects_with_geometry(
        scenario_id, user, physical_object_type_id, physical_object_function_id, include_scenario_objects
    )
    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in physical_objects], centers_only)


@physical_objects_mcp.tool(
    name="GetTerritoryPhysicalObjects",
    title="Получить физические объекты территории ",
    description="""Возвращает физические объекты территории с курсорной пагинацией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    name | Optional[str] | нет | Фильтр по подстроке в названии.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки.
    cursor | Optional[str] | нет | Курсор следующей страницы.
    page_size | int | нет | Размер страницы.
    
    Выходные данные:
    MCPCursorPage[PhysicalObject] | Страница физических объектов с курсором.
    
    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list | Элементы текущей страницы.
    count | int | Общее количество элементов.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.
    
    PhysicalObject:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    territories | list[ShortTerritory] | None | Территории объекта.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    
    Пример вызова:
    {"tool": "GetTerritoryPhysicalObjects", "arguments": {"territory_id": 10, "physical_object_type_id": 4, "page_size": 10}}
    
    Пример результата:
    {"items": [{"physical_object_id": 25, "name": "Школа N 1"...}], "count": 1, "page_size": 10, "prevCursor": null, "nextCursor": "eyJsYXN0X2lkIjoyfQ=="}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32001 Not found: территория, тип или функция физического объекта не найдены.
    """,
    tags=["physical_objects", "territories", ""],
    annotations={"title": "GetTerritoryPhysicalObjects", "readOnlyHint": True},
)
async def get_physical_objects_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    name: Annotated[Optional[str], "Фильтр по названию"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор следующей страницы"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[PhysicalObject]:
    """Get physical objects for territory with cursor pagination."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    order_by_value = order_by.value if order_by is not None else None
    params = MCPCursorParams(cursor=cursor, size=page_size)
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
        params=params,
    )
    return MCPCursorPage.create(
        [PhysicalObject.from_dto(item) for item in physical_objects.items],
        params=params,
        total=physical_objects.total,
        **(physical_objects.cursor_data or {}),
    )


@physical_objects_mcp.tool(
    name="GetTerritoryPhysicalObjectsWithGeometry",
    title="Получить физические объекты территории с геометрией ",
    description="""Возвращает физические объекты территории с геометрией и курсорной пагинацией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта; нельзя сочетать с physical_object_function_id.
    physical_object_function_id | Optional[int] | нет | Фильтр по функции физического объекта; нельзя сочетать с physical_object_type_id.
    name | Optional[str] | нет | Фильтр по подстроке в названии.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки.
    cursor | Optional[str] | нет | Курсор следующей страницы.
    page_size | int | нет | Размер страницы.
    
    Выходные данные:
    MCPCursorPage[PhysicalObjectWithGeometry] | Страница физических объектов с геометрией и курсором.
    
    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list | Элементы текущей страницы.
    count | int | Общее количество элементов.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.
    
    PhysicalObjectWithGeometry:
    Поле | Тип | Описание
    physical_object_id | int | Идентификатор физического объекта.
    physical_object_type | PhysicalObjectType | Тип физического объекта и его функция.
    territory | ShortTerritory | Территория размещения геометрии.
    name | str | None | Название физического объекта.
    properties | dict | Дополнительные свойства.
    building | ShortBuilding | None | Связанное здание.
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    geometry | Geometry | Геометрия объекта.
    centre_point | Point | Центр геометрии.
    created_at | datetime | Дата и время создания.
    updated_at | datetime | Дата и время обновления.
    
    Пример вызова:
    {"tool": "GetTerritoryPhysicalObjectsWithGeometry", "arguments": {"territory_id": 10, "physical_object_function_id": 2, "page_size": 10}}
    
    Пример результата:
    {"items": [{"physical_object_id": 25, "object_geometry_id": 100, "name": "Школа N 1"...}], "page_size": 10, "prevCursor": null, "nextCursor": "eyJsYXN0X2lkIjoyfQ=="}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и physical_object_function_id.
    - -32001 Not found: территория, тип, функция или геометрия объекта не найдены.
    """,
    tags=["physical_objects", "territories", ""],
    annotations={"title": "GetTerritoryPhysicalObjectsWithGeometry", "readOnlyHint": True},
)
async def get_physical_objects_with_geometry_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    physical_object_function_id: Annotated[Optional[int], "Фильтр по функции физического объекта"] = None,
    name: Annotated[Optional[str], "Фильтр по названию"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор следующей страницы"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[PhysicalObjectWithGeometry]:
    """Get physical objects with geometry for territory with cursor pagination."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_type_or_function(physical_object_type_id, physical_object_function_id)
    order_by_value = order_by.value if order_by is not None else None
    params = MCPCursorParams(cursor=cursor, size=page_size)
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
        params=params,
    )
    return MCPCursorPage.create(
        [PhysicalObjectWithGeometry.from_dto(item) for item in physical_objects.items],
        params=params,
        total=physical_objects.total,
        **(physical_objects.cursor_data or {}),
    )
