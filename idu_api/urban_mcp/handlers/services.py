"""MCP tools for services and service types are defined here."""

from typing import Annotated, Optional

from fastmcp import Context
from fastmcp.dependencies import CurrentRequest, Depends
from fastmcp.server.dependencies import CurrentContext
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.logic.service_types import ServiceTypesService
from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    PhysicalObjectType,
    ScenarioService,
    ScenarioServiceWithGeometryAttributes,
    Service,
    ServicesCountCapacity,
    ServiceType,
    ServiceTypesHierarchy,
    ServiceWithGeometry,
    SocGroupWithServiceTypes,
    SocValue,
    UrbanFunction,
)
from idu_api.urban_api.schemas.enums import OrderByField, Ordering
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_api.schemas.pages import MCPCursorPage, MCPCursorParams
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import dictionaries_mcp, projects_mcp, soc_groups_mcp, territories_mcp


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


def _validate_service_type_or_function(service_type_id: int | None, urban_function_id: int | None) -> None:
    if service_type_id is not None and urban_function_id is not None:
        raise McpError(
            ErrorData(code=-32602, message="Укажите только один фильтр: service_type_id или urban_function_id.")
        )


@dictionaries_mcp.tool(
    name="GetServiceTypes",
    title="Получить типы сервисов",
    description="""Возвращает типы сервисов с фильтрами по городской функции и названию.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    urban_function_id | Optional[int] | нет | Фильтр по идентификатору городской функции.
    name | Optional[str] | нет | Фильтр по подстроке названия типа сервиса без учета регистра.
    
    Выходные данные:
    list[ServiceType] | Список типов сервисов.
    
    Поля модели:
    ServiceType:
    Поле | Тип | Описание
    service_type_id | int | Идентификатор типа сервиса.
    urban_function | UrbanFunctionBasic | Городская функция, к которой относится тип сервиса.
    name | str | Название типа сервиса.
    capacity_modeled | int | None | Модельная мощность по умолчанию.
    code | str | Код типа сервиса.
    infrastructure_type | Optional | Тип инфраструктуры.
    properties | dict | Дополнительные свойства типа сервиса.
    
    Пример вызова:
    {"tool": "GetServiceTypes", "arguments": {"urban_function_id": 2, "name": "школа"}}
    
    Пример результата:
    [{"service_type_id": 7, "urban_function": {"id": 2, "name": "Образование"}, "name": "Школьное образование", "capacity_modeled": 500, "code": "school", "infrastructure_type": "basic", "properties": {}}]
    
    Ошибки:
    - -32001 Not found: городская функция не найдена или по фильтрам нет доступных типов сервисов.
    """,
    tags=["services"],
    annotations={"title": "GetServiceTypes", "readOnlyHint": True},
)
async def get_service_types(
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по подстроке названия"] = None,
    request: Request = CurrentRequest(),
) -> list[ServiceType]:
    """Get all service types."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    service_types = await service_types_service.get_service_types(urban_function_id, name)
    return [ServiceType.from_dto(service_type) for service_type in service_types]


@dictionaries_mcp.tool(
    name="GetUrbanFunctionsByParent",
    title="Получить городские функции по родителю",
    description="""Возвращает городские функции из иерархии по родительской функции и фильтру названия.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской городской функции; если не указан, возвращаются функции верхнего уровня.
    name | Optional[str] | нет | Фильтр по подстроке названия без учета регистра.
    get_all_subtree | bool | нет | Если true, возвращается все поддерево родительской функции.
    
    Выходные данные:
    list[UrbanFunction] | Список городских функций.
    
    Поля модели:
    UrbanFunction:
    Поле | Тип | Описание
    urban_function_id | int | Идентификатор городской функции.
    parent_urban_function | UrbanFunctionBasic | None | Родительская городская функция.
    name | str | Название городской функции.
    level | int | Уровень в иерархии.
    list_label | str | Маркер в иерархическом списке.
    code | str | Код городской функции.
    
    Пример вызова:
    {"tool": "GetUrbanFunctionsByParent", "arguments": {"parent_id": 1, "name": "образ", "get_all_subtree": false}}
    
    Пример результата:
    [{"urban_function_id": 2, "parent_urban_function": {"id": 1, "name": "Социальная инфраструктура"}, "name": "Образование", "level": 2, "list_label": "1.1", "code": "EDU"}]
    
    Ошибки:
    - -32001 Not found: родительская городская функция не найдена.
    """,
    tags=["services"],
    annotations={"title": "GetUrbanFunctionsByParent", "readOnlyHint": True},
)
async def get_urban_functions_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской городской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по подстроке названия"] = None,
    get_all_subtree: Annotated[bool, "Вернуть все поддерево"] = False,
    request: Request = CurrentRequest(),
) -> list[UrbanFunction]:
    """Get urban functions by parent identifier."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    urban_functions = await service_types_service.get_urban_functions_by_parent_id(parent_id, name, get_all_subtree)
    return [UrbanFunction.from_dto(urban_function) for urban_function in urban_functions]


@dictionaries_mcp.tool(
    name="GetServiceTypesHierarchy",
    title="Получить иерархию типов сервисов",
    description="""Возвращает иерархию городских функций с вложенными типами сервисов.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_types_ids | Optional[str] | нет | Список идентификаторов типов сервисов через запятую; если указан, дерево ограничивается этими типами.
    
    Выходные данные:
    list[ServiceTypesHierarchy] | Дерево городских функций и типов сервисов.
    
    Поля модели:
    ServiceTypesHierarchy:
    Поле | Тип | Описание
    urban_function_id | int | Идентификатор городской функции.
    parent_id | int | None | Идентификатор родительской функции.
    name | str | Название функции.
    level | int | Уровень в дереве.
    list_label | str | Маркер в иерархическом списке.
    code | str | Код функции.
    children | list | Дочерние функции или типы сервисов.
    
    Пример вызова:
    {"tool": "GetServiceTypesHierarchy", "arguments": {"service_types_ids": "7,8"}}
    
    Пример результата:
    [{"urban_function_id": 2, "parent_id": 1, "name": "Образование", "level": 2, "list_label": "1.1", "code": "EDU", "children": [{"service_type_id": 7, "name": "Школьное образование"}]}]
    
    Ошибки:
    - -32602 Invalid params: service_types_ids содержит нецелочисленное значение.
    - -32001 Not found: один из типов сервисов не найден.
    """,
    tags=["services"],
    annotations={"title": "GetServiceTypesHierarchy", "readOnlyHint": True},
)
async def get_service_types_hierarchy(
    service_types_ids: Annotated[Optional[str], "Список идентификаторов типов сервисов через запятую"] = None,
    request: Request = CurrentRequest(),
) -> list[ServiceTypesHierarchy]:
    """Get service types hierarchy."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    hierarchy = await service_types_service.get_service_types_hierarchy(_parse_ids(service_types_ids))
    return [ServiceTypesHierarchy.from_dto(node) for node in hierarchy]


@dictionaries_mcp.tool(
    name="GetPhysicalObjectTypesByServiceType",
    title="Получить типы физических объектов по типу сервиса",
    description="""Возвращает типы физических объектов, совместимые с указанным типом сервиса.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | int | да | Идентификатор типа сервиса.
    
    Выходные данные:
    list[PhysicalObjectType] | Список совместимых типов физических объектов.
    
    Поля модели:
    PhysicalObjectType:
    Поле | Тип | Описание
    physical_object_type_id | int | Идентификатор типа физического объекта.
    name | str | Название типа физического объекта.
    physical_object_function | PhysicalObjectFunctionBasic | Функция физического объекта.
    
    Пример вызова:
    {"tool": "GetPhysicalObjectTypesByServiceType", "arguments": {"service_type_id": 7}}
    
    Пример результата:
    [{"physical_object_type_id": 4, "name": "Школа", "physical_object_function": {"id": 2, "name": "Образование"}}]
    
    Ошибки:
    - -32001 Not found: тип сервиса не найден.
    """,
    tags=["services", "physical_objects"],
    annotations={"title": "GetPhysicalObjectTypesByServiceType", "readOnlyHint": True},
)
async def get_physical_object_types(
    service_type_id: Annotated[int, "Идентификатор типа сервиса"],
    request: Request = CurrentRequest(),
) -> list[PhysicalObjectType]:
    """Get physical object types by service type."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    types = await service_types_service.get_physical_object_types_by_service_type(service_type_id)
    return [PhysicalObjectType.from_dto(object_type) for object_type in types]


@soc_groups_mcp.tool(
    name="GetSocialValuesByServiceType",
    title="Получить социальные ценности по типу сервиса",
    description="""Возвращает социальные ценности, связанные с указанным типом сервиса.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | int | да | Идентификатор типа сервиса.
    
    Выходные данные:
    list[SocValue] | Список социальных ценностей типа сервиса.
    
    Поля модели:
    SocValue:
    Поле | Тип | Описание
    soc_value_id | int | Идентификатор социальной ценности.
    name | str | Название социальной ценности.
    rank | int | Ранг социальной ценности.
    normative_value | float | Нормативное значение.
    decree_value | float | Значение по нормативному акту.
    
    Пример вызова:
    {"tool": "GetSocialValuesByServiceType", "arguments": {"service_type_id": 7}}
    
    Пример результата:
    [{"soc_value_id": 3, "name": "Доступность образования", "rank": 1, "normative_value": 1.0, "decree_value": 1.0}]
    
    Ошибки:
    - -32001 Not found: тип сервиса не найден.
    """,
    tags=["services"],
    annotations={"title": "GetSocialValuesByServiceType", "readOnlyHint": True},
)
async def get_social_values(
    service_type_id: Annotated[int, "Идентификатор типа сервиса"],
    request: Request = CurrentRequest(),
) -> list[SocValue]:
    """Get social values by service type."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    soc_values = await service_types_service.get_social_values_by_service_type_id(service_type_id)
    return [SocValue.from_dto(value) for value in soc_values]


@soc_groups_mcp.tool(
    name="GetSocialGroupsByServiceType",
    title="Получить социальные группы по типу сервиса",
    description="""Возвращает социальные группы, для которых релевантен указанный тип сервиса.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | int | да | Идентификатор типа сервиса.
    
    Выходные данные:
    list[SocGroupWithServiceTypes] | Список социальных групп с привязанными типами сервисов.
    
    Поля модели:
    SocGroupWithServiceTypes:
    Поле | Тип | Описание
    soc_group_id | int | Идентификатор социальной группы.
    name | str | Название социальной группы.
    service_types | list | Типы сервисов, связанные с группой.
    
    Пример вызова:
    {"tool": "GetSocialGroupsByServiceType", "arguments": {"service_type_id": 7}}
    
    Пример результата:
    [{"soc_group_id": 2, "name": "Дети школьного возраста", "service_types": [{"id": 7, "name": "Школьное образование"}]}]
    
    Ошибки:
    - -32001 Not found: тип сервиса не найден.
    """,
    tags=["services"],
    annotations={"title": "GetSocialGroupsByServiceType", "readOnlyHint": True},
)
async def get_social_groups(
    service_type_id: Annotated[int, "Идентификатор типа сервиса"],
    request: Request = CurrentRequest(),
) -> list[SocGroupWithServiceTypes]:
    """Get social groups by service type."""
    service_types_service: ServiceTypesService = request.state.service_types_service
    soc_groups = await service_types_service.get_social_groups_by_service_type_id(service_type_id)
    return [SocGroupWithServiceTypes.from_dto(group) for group in soc_groups]


@territories_mcp.tool(
    name="GetServiceTypesByTerritoryId",
    title="Получить типы сервисов на территории",
    description="""Возвращает типы сервисов, представленные на указанной территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    list[ServiceType] | Список типов сервисов территории.
    
    Поля модели:
    ServiceType:
    Поле | Тип | Описание
    service_type_id | int | Идентификатор типа сервиса.
    urban_function | UrbanFunctionBasic | Городская функция.
    name | str | Название типа сервиса.
    capacity_modeled | int | None | Модельная мощность.
    code | str | Код типа сервиса.
    infrastructure_type | Optional | Тип инфраструктуры.
    properties | dict | Дополнительные свойства.
    
    Пример вызова:
    {"tool": "GetServiceTypesByTerritoryId", "arguments": {"territory_id": 10, "include_child_territories": true, "cities_only": false}}
    
    Пример результата:
    [{"service_type_id": 7, "urban_function": {"id": 2, "name": "Образование"}, "name": "Школьное образование", "capacity_modeled": 500, "code": "school", "infrastructure_type": "basic", "properties": {}}]
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория не найдена.
    """,
    tags=["services"],
    annotations={"title": "GetServiceTypesByTerritoryId", "readOnlyHint": True},
)
async def get_service_types_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    request: Request = CurrentRequest(),
) -> list[ServiceType]:
    """Get service types by territory identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    service_types = await territories_service.get_service_types_by_territory_id(
        territory_id, include_child_territories, cities_only
    )
    return [ServiceType.from_dto(service_type) for service_type in service_types]


@territories_mcp.tool(
    name="GetTerritoryServicesGeoJSON",
    title="Получить сервисы на территории в GeoJSON",
    description="""Возвращает сервисы территории в формате GeoJSON с возможностью вернуть центры вместо геометрии.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    name | Optional[str] | нет | Фильтр по подстроке названия сервиса.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ServiceWithGeometry]] | GeoJSON FeatureCollection с сервисами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
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
    created_at | datetime | Дата и время создания сервиса.
    updated_at | datetime | Дата и время последнего обновления сервиса.
    
    Пример вызова:
    {"tool": "GetTerritoryServicesGeoJSON", "arguments": {"territory_id": 10, "service_type_id": 7, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"service_id": 30, "object_geometry_id": 100, "name": "Школьное образование"}}]}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32001 Not found: территория, тип сервиса или городская функция не найдены.
    """,
    tags=["services", "territories"],
    annotations={"title": "GetTerritoryServicesGeoJSON", "readOnlyHint": True},
)
async def get_services_geojson_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по подстроке названия"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, Service]]:
    """Get territory services in GeoJSON format."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_service_type_or_function(service_type_id, urban_function_id)
    services = await territories_service.get_services_with_geometry_by_territory_id(
        territory_id,
        service_type_id,
        urban_function_id,
        name,
        include_child_territories,
        cities_only,
        None,
        "asc",
        paginate=False,
    )
    return await GeoJSONResponse.from_list([service.to_geojson_dict() for service in services], centers_only)


@territories_mcp.tool(
    name="GetTerritoryServicesCapacity",
    title="Получить количество и вместимость сервисов территории",
    description="""Возвращает агрегированное количество и суммарную вместимость сервисов на уровне дочерних территорий.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор родительской территории.
    level | int | да | Уровень территорий, по которым нужно агрегировать значения.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса.
    
    Выходные данные:
    list[ServicesCountCapacity] | Список агрегатов по территориям.
    
    Поля модели:
    ServicesCountCapacity:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    count | int | Количество сервисов на территории.
    capacity | int | Суммарная мощность сервисов на территории.
    
    Пример вызова:
    {"tool": "GetTerritoryServicesCapacity", "arguments": {"territory_id": 10, "level": 2, "service_type_id": 7}}
    
    Пример результата:
    [{"territory_id": 11, "count": 5, "capacity": 2500}]
    
    Ошибки:
    - -32001 Not found: территория или тип сервиса не найдены.
    """,
    tags=["services", "territories"],
    annotations={"title": "GetTerritoryServicesCapacity", "readOnlyHint": True},
)
async def get_total_services_capacity_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    level: Annotated[int, "Уровень территории"],
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    request: Request = CurrentRequest(),
) -> list[ServicesCountCapacity]:
    """Get service capacity by territory identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    services = await territories_service.get_services_capacity_by_territory_id(territory_id, level, service_type_id)
    return [ServicesCountCapacity.from_dto(s) for s in services]


@projects_mcp.tool(
    name="GetScenarioServiceTypes",
    title="Получить типы сервисов сценария",
    description="""Возвращает типы сервисов текущего сценария или его контекста.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    for_context | bool | нет | Если true, возвращаются типы сервисов контекста сценария; иначе типы сервисов объектов сценария.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ServiceType] | Список типов сервисов сценария или контекста.
    
    Поля модели:
    ServiceType:
    Поле | Тип | Описание
    service_type_id | int | Идентификатор типа сервиса.
    urban_function | UrbanFunctionBasic | Городская функция.
    name | str | Название типа сервиса.
    capacity_modeled | int | None | Модельная мощность.
    code | str | Код типа сервиса.
    infrastructure_type | Optional | Тип инфраструктуры.
    properties | dict | Дополнительные свойства.
    
    Пример вызова:
    {"tool": "GetScenarioServiceTypes", "arguments": {"for_context": false}}
    
    Пример результата:
    [{"service_type_id": 7, "urban_function": {"id": 2, "name": "Образование"}, "name": "Школьное образование", "capacity_modeled": 500, "code": "school", "infrastructure_type": "basic", "properties": {}}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий не найден.
    """,
    tags=["services"],
    annotations={"title": "GetScenarioServiceTypes", "readOnlyHint": True},
)
async def get_service_types_by_scenario_id(
    for_context: Annotated[bool, "Вернуть типы сервисов контекста"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ServiceType]:
    """Get service types by current scenario identifier."""
    user_project_service: UserProjectService = request.state.user_project_service
    types = await user_project_service.get_service_types_by_scenario_id_from_db(
        _get_scenario_id(context), user, for_context
    )
    return [ServiceType.from_dto(service_type) for service_type in types]


@projects_mcp.tool(
    name="GetScenarioServices",
    title="Получить сервисы сценария",
    description="""Возвращает список сервисов текущего сценария с фильтрами по типу сервиса или городской функции.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ScenarioService] | Список сервисов сценария.
    
    Поля модели:
    ScenarioService:
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
    is_scenario_object | bool | Признак сервиса, созданного или измененного в сценарии.
    is_locked | bool | Признак блокировки сервиса для редактирования.
    
    Пример вызова:
    {"tool": "GetScenarioServices", "arguments": {"service_type_id": 7}}
    
    Пример результата:
    [{"service_id": 30, "name": "Школьное образование", "capacity": 500, "is_scenario_object": true, "is_locked": false}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип сервиса или городская функция не найдены.
    """,
    tags=["services"],
    annotations={"title": "GetScenarioServices", "readOnlyHint": True},
)
async def get_services_by_scenario_id(
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ScenarioService]:
    """Get services by current scenario identifier."""
    user_project_service: UserProjectService = request.state.user_project_service
    _validate_service_type_or_function(service_type_id, urban_function_id)
    services = await user_project_service.get_services_by_scenario_id(
        _get_scenario_id(context), user, service_type_id, urban_function_id
    )
    return [ScenarioService.from_dto(service) for service in services]


@projects_mcp.tool(
    name="GetScenarioServicesWithGeometry",
    title="Получить сервисы сценария с геометрией",
    description="""Возвращает сервисы текущего сценария в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioServiceWithGeometryAttributes]] | GeoJSON FeatureCollection с сервисами сценария.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioServiceWithGeometryAttributes:
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
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    is_scenario_service | bool | Признак сценарного сервиса.
    is_scenario_geometry | bool | Признак сценарной геометрии.
    is_locked | bool | Признак блокировки сервиса для редактирования.
    
    Пример вызова:
    {"tool": "GetScenarioServicesWithGeometry", "arguments": {"service_type_id": 7, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"service_id": 30, "object_geometry_id": 100, "is_scenario_service": true, "is_locked": false}}]}
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип сервиса или городская функция не найдены.
    """,
    tags=["services"],
    annotations={"title": "GetScenarioServicesWithGeometry", "readOnlyHint": True},
)
async def get_services_with_geometry_by_scenario_id(
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioServiceWithGeometryAttributes]]:
    """Get scenario services with geometry."""
    user_project_service: UserProjectService = request.state.user_project_service
    _validate_service_type_or_function(service_type_id, urban_function_id)
    services = await user_project_service.get_services_with_geometry_by_scenario_id(
        _get_scenario_id(context), user, service_type_id, urban_function_id
    )
    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in services], centers_only)


@projects_mcp.tool(
    name="GetContextServices",
    title="Получить сервисы контекста",
    description="""Возвращает список сервисов контекста текущего сценария с фильтрами по типу сервиса или городской функции.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ScenarioService] | Список сервисов контекста.
    
    Поля модели:
    ScenarioService:
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
    is_scenario_object | bool | Признак сервиса, созданного или измененного в сценарии.
    is_locked | bool | Признак блокировки сервиса для редактирования.
    
    Пример вызова:
    {"tool": "GetContextServices", "arguments": {"urban_function_id": 2}}
    
    Пример результата:
    [{"service_id": 30, "name": "Школьное образование", "capacity": 500, "is_scenario_object": false, "is_locked": false}]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип сервиса или городская функция не найдены.
    """,
    tags=["services", "context"],
    annotations={"title": "GetContextServices", "readOnlyHint": True},
)
async def get_context_services(
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ScenarioService]:
    """Get context services for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    _validate_service_type_or_function(service_type_id, urban_function_id)
    services = await user_project_service.get_context_services(
        _get_scenario_id(context), user, service_type_id, urban_function_id
    )
    return [ScenarioService.from_dto(service) for service in services]


@projects_mcp.tool(
    name="GetContextServicesWithGeometry",
    title="Получить сервисы контекста с геометрией",
    description="""Возвращает сервисы контекста текущего сценария в GeoJSON вместе с геометрией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    include_scenario_objects | bool | нет | Если true, вместе с контекстом включаются сервисы сценария.
    centers_only | bool | нет | Если true, возвращаются центры геометрий.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioServiceWithGeometryAttributes]] | GeoJSON FeatureCollection с сервисами контекста.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioServiceWithGeometryAttributes:
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
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    is_scenario_service | bool | Признак сценарного сервиса.
    is_scenario_geometry | bool | Признак сценарной геометрии.
    is_locked | bool | Признак блокировки сервиса для редактирования.
    
    Пример вызова:
    {"tool": "GetContextServicesWithGeometry", "arguments": {"urban_function_id": 2, "include_scenario_objects": true, "centers_only": false}}
    
    Пример результата:
    {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [56.25, 58.01]}, "properties": {"service_id": 30, "object_geometry_id": 100, "is_scenario_service": false, "is_locked": false}}]}
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип сервиса или городская функция не найдены.
    """,
    tags=["services", "context"],
    annotations={"title": "GetContextServicesWithGeometry", "readOnlyHint": True},
)
async def get_context_services_with_geometry(
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    include_scenario_objects: Annotated[bool, "Включать объекты сценария"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioServiceWithGeometryAttributes]]:
    """Get context services with geometry for current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    _validate_service_type_or_function(service_type_id, urban_function_id)
    services = await user_project_service.get_context_services_with_geometry(
        _get_scenario_id(context), user, service_type_id, urban_function_id, include_scenario_objects
    )
    return await GeoJSONResponse.from_list([obj.to_geojson_dict() for obj in services], centers_only)


@territories_mcp.tool(
    name="GetTerritoryServices",
    title="Получить страницу сервисов на территории",
    description="""Постранично возвращает сервисы на территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    name | Optional[str] | нет | Фильтр по подстроке названия сервиса.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки.
    cursor | Optional[str] | нет | Курсор следующей страницы.
    page_size | int | нет | Размер страницы.
    
    Выходные данные:
    MCPCursorPage[Service] | Страница сервисов с курсором.
    
    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list | Элементы текущей страницы.
    count | int | Общее количество элементов.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.
    
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
    {"tool": "GetTerritoryServices", "arguments": {"territory_id": 10, "service_type_id": 7}}
    
    Пример результата:
    {"items": [{"service_id": 30, "name": "Школьное образование", "capacity": 500}], "count": 1, "page_size": 10, "prevCursor": null, "nextCursor": "eyJsYXN0X2lkIjoyfQ=="}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32001 Not found: территория, тип сервиса или городская функция не найдены.
    """,
    tags=["services", "territories", ""],
    annotations={"title": "GetTerritoryServices", "readOnlyHint": True},
)
async def get_services_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по подстроке названия"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор следующей страницы"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[Service]:
    """Get services by territory identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_service_type_or_function(service_type_id, urban_function_id)
    params = MCPCursorParams(cursor=cursor, size=page_size)
    services = await territories_service.get_services_by_territory_id(
        territory_id,
        service_type_id,
        urban_function_id,
        name,
        include_child_territories,
        cities_only,
        order_by.value if order_by is not None else None,
        ordering.value,
        paginate=True,
        params=params,
    )
    return MCPCursorPage.create(
        [Service.from_dto(item) for item in services.items],
        params=params,
        total=services.total,
        **(services.cursor_data or {}),
    )


@territories_mcp.tool(
    name="GetTerritoryServicesWithGeometry",
    title="Получить сервисы территории с геометрией ",
    description="""Возвращает сервисы территории с геометрией и курсорной пагинацией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса; нельзя сочетать с urban_function_id.
    urban_function_id | Optional[int] | нет | Фильтр по городской функции; нельзя сочетать с service_type_id.
    name | Optional[str] | нет | Фильтр по подстроке названия сервиса.
    include_child_territories | bool | нет | Если true, учитываются дочерние территории.
    cities_only | bool | нет | Если true, учитываются только дочерние города; допустимо только при include_child_territories=true.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки.
    cursor | Optional[str] | нет | Курсор следующей страницы.
    page_size | int | нет | Размер страницы.
    
    Выходные данные:
    MCPCursorPage[ServiceWithGeometry] | Страница сервисов с геометрией и курсором.
    
    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list | Элементы текущей страницы.
    count | int | Общее количество элементов.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.
    
    ServiceWithGeometry:
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
    object_geometry_id | int | Идентификатор геометрии объекта.
    address | str | None | Адрес геометрии.
    osm_id | str | None | Идентификатор OpenStreetMap.
    
    Пример вызова:
    {"tool": "GetTerritoryServicesWithGeometry", "arguments": {"territory_id": 10, "urban_function_id": 2}}
    
    Пример результата:
    {"items": [{"service_id": 30, "object_geometry_id": 100, "name": "Школьное образование"}], "count": 1, "page_size": 10, "prevCursor": null, "nextCursor": "eyJsYXN0X2lkIjoyfQ=="}
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы service_type_id и urban_function_id.
    - -32001 Not found: территория, тип сервиса или городская функция не найдены.
    """,
    tags=["services", "territories", ""],
    annotations={"title": "GetTerritoryServicesWithGeometry", "readOnlyHint": True},
)
async def get_services_with_geometry_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    service_type_id: Annotated[Optional[int], "Идентификатор типа сервиса"] = None,
    urban_function_id: Annotated[Optional[int], "Идентификатор городской функции"] = None,
    name: Annotated[Optional[str], "Фильтр по подстроке названия"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор следующей страницы"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[ServiceWithGeometry]:
    """Get services with geometry by territory identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_child_territories(include_child_territories, cities_only)
    _validate_service_type_or_function(service_type_id, urban_function_id)
    params = MCPCursorParams(cursor=cursor, size=page_size)
    services = await territories_service.get_services_with_geometry_by_territory_id(
        territory_id,
        service_type_id,
        urban_function_id,
        name,
        include_child_territories,
        cities_only,
        order_by.value if order_by is not None else None,
        ordering.value,
        paginate=True,
        params=params,
    )
    return MCPCursorPage.create(
        [ServiceWithGeometry.from_dto(item) for item in services.items],
        params=params,
        total=services.total,
        **(services.cursor_data or {}),
    )
