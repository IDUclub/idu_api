"""MCP tools for buffers are defined here."""

from typing import Annotated, Optional

from fastmcp.dependencies import CurrentRequest, Depends
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.buffers import BufferService
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import BufferAttributes, BufferType, DefaultBufferValue, ScenarioBufferAttributes
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import dictionaries_mcp, projects_mcp, territories_mcp


@dictionaries_mcp.tool(
    name="GetBufferTypes",
    title="Получить типы зон ограничений",
    description="""Возвращает справочник типов зон ограничений, которые используются для построения санитарных, охранных и иных буферов вокруг городских объектов.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[BufferType] | Список доступных типов зон ограничений.
    
    Поля модели:
    BufferType:
    Поле | Тип | Описание
    buffer_type_id | int | Идентификатор типа зоны ограничений.
    name | str | Название типа зоны ограничений.
    description | str | None | Описание назначения и правил применения типа зоны ограничений.
    
    Пример вызова:
    {
      "tool": "GetBufferTypes",
      "arguments": {}
    }
    
    Пример результата:
    [
      {
        "buffer_type_id": 1,
        "name": "Санитарно-защитная зона",
        "description": "Буферная зона вокруг объектов с нормативными ограничениями."
      }
    ]
    """,
    tags=["buffers"],
    annotations={"title": "GetBufferTypes", "readOnlyHint": True},
)
async def get_buffer_types(request: Request = CurrentRequest()) -> list[BufferType]:
    """Get a list of all buffer types."""
    buffers_service: BufferService = request.state.buffers_service
    buffer_types = await buffers_service.get_buffer_types()
    return [BufferType.from_dto(zone_type) for zone_type in buffer_types]


@dictionaries_mcp.tool(
    name="GetDefaultBufferValues",
    title="Получить нормативные значения радиусов зон ограничений",
    description="""Возвращает нормативные радиусы зон ограничений для сочетаний типа зоны ограничений с типом физического объекта или типом сервиса.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[DefaultBufferValue] | Список нормативных значений радиусов зон ограничений.
    
    Поля модели:
    DefaultBufferValue:
    Поле | Тип | Описание
    buffer_type | BufferTypeBasic | Тип зоны ограничений, для которого задан радиус.
    physical_object_type | PhysicalObjectTypeBasic | None | Тип физического объекта; заполняется, если радиус относится к физическим объектам.
    service_type | ServiceTypeBasic | None | Тип сервиса; заполняется, если радиус относится к сервисам.
    buffer_value | float | Нормативный радиус зоны ограничений в метрах.
    
    Пример вызова:
    {
      "tool": "GetDefaultBufferValues",
      "arguments": {}
    }
    
    Пример результата:
    [
      {
        "buffer_type": {"id": 1, "name": "Санитарно-защитная зона"},
        "physical_object_type": {"id": 12, "name": "Промышленный объект"},
        "service_type": null,
        "buffer_value": 300.0
      }
    ]
    """,
    tags=["buffers"],
    annotations={"title": "GetDefaultBufferValues", "readOnlyHint": True},
)
async def get_default_buffer_values(request: Request = CurrentRequest()) -> list[DefaultBufferValue]:
    """Get default buffer values for all buffer types."""
    buffers_service: BufferService = request.state.buffers_service
    values = await buffers_service.get_all_default_buffer_values()
    return [DefaultBufferValue.from_dto(value) for value in values]


@territories_mcp.tool(
    name="GetTerritoryBuffersGeoJSON",
    title="Получить зоны ограничений объектов территории в формате GeoJSON",
    description="""Возвращает зоны ограничений городских объектов на указанной территории в формате GeoJSON с возможностью фильтрации по типу зоны ограничения, типу физического объекта или типу сервиса.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, для которой нужно получить зоны ограничений.
    buffer_type_id | Optional[int] | нет | Фильтр по типу зоны ограничений.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта. Нельзя использовать одновременно с service_type_id.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса. Нельзя использовать одновременно с physical_object_type_id.
    include_child_territories | bool | нет | Если true, в выборку включаются объекты дочерних территорий.
    cities_only | bool | нет | Если true, учитываются только дочерние территории-городa; допустимо только при include_child_territories=true.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, BufferAttributes]] | GeoJSON FeatureCollection с геометрией зон ограничений и атрибутами связанных объектов.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    BufferAttributes:
    Поле | Тип | Описание
    buffer_type | BufferTypeBasic | Тип зоны ограничений, которым построена зона.
    urban_object | ShortUrbanObject | Городской объект, вокруг которого построена зона ограничений.
    is_custom | bool | Признак пользовательского значения радиуса вместо значения по умолчанию.
    
    Пример вызова:
    {
      "tool": "GetTerritoryBuffersGeoJSON",
      "arguments": {
        "territory_id": 1,
        "buffer_type_id": 2,
        "physical_object_type_id": 12,
        "include_child_territories": true
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
            "buffer_type": {"id": 2, "name": "Санитарно-защитная зона"},
            "urban_object": {"id": 10, "name": "Промышленный объект"},
            "is_custom": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и service_type_id.
    - -32001 Not found: территория, тип зоны ограничений, тип физического объекта или тип сервиса не найдены.
    """,
    tags=["buffers"],
    annotations={"title": "GetTerritoryBuffersGeoJSON", "readOnlyHint": True},
)
async def get_buffers_geojson_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    buffer_type_id: Annotated[Optional[int], "Фильтр по типу зоны ограничений"] = None,
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Только города"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, BufferAttributes]]:
    """Get buffers for a territory in GeoJSON format."""
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )

    if physical_object_type_id is not None and service_type_id is not None:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Укажите только один фильтр: physical_object_type_id или service_type_id.",
            )
        )

    buffers = await territories_service.get_buffers_by_territory_id(
        territory_id,
        include_child_territories,
        cities_only,
        buffer_type_id,
        physical_object_type_id,
        service_type_id,
    )

    return await GeoJSONResponse.from_list((buffer.to_geojson_dict() for buffer in buffers))


@projects_mcp.tool(
    name="GetScenarioBuffers",
    title="Получить зоны ограничений объектов сценария",
    description="""Возвращает зоны ограничений объектов проектной территории текущего сценария в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    buffer_type_id | Optional[int] | нет | Фильтр по типу зоны ограничений.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта. Нельзя использовать одновременно с service_type_id.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса. Нельзя использовать одновременно с physical_object_type_id.
    scenario_id | int | да | Идентификатор сценария в arguments MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioBufferAttributes]] | GeoJSON FeatureCollection с зонами ограничений объектов сценария.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioBufferAttributes:
    Поле | Тип | Описание
    buffer_type | BufferTypeBasic | Тип зоны ограничений, которым построена зона.
    urban_object | ShortUrbanObject | Объект сценария или базовый городской объект, вокруг которого построена зона ограничений.
    is_custom | bool | Признак пользовательского значения радиуса.
    is_scenario_object | bool | Признак того, что объект создан или изменен в сценарии.
    is_locked | bool | Признак блокировки объекта для изменений.
    
    Пример вызова:
    {
      "tool": "GetScenarioBuffers",
      "arguments": {
        "buffer_type_id": 2,
        "service_type_id": 5
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
            "buffer_type": {"id": 2, "name": "Санитарно-защитная зона"},
            "urban_object": {"id": 20, "name": "Детский сад"},
            "is_custom": false,
            "is_scenario_object": true,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: одновременно переданы physical_object_type_id и service_type_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип зоны ограничений, тип физического объекта или тип сервиса не найдены.
    """,
    tags=["buffers"],
    annotations={"title": "GetScenarioBuffers", "readOnlyHint": True},
)
async def get_buffers_by_scenario_id(
    scenario_id: Annotated[int, "Идентификатор сценария"],
    buffer_type_id: Annotated[Optional[int], "Фильтр по типу зоны ограничений"] = None,
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    request: Request = CurrentRequest(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioBufferAttributes]]:
    """Get buffers for a scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service

    if physical_object_type_id is not None and service_type_id is not None:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Укажите только один фильтр: physical_object_type_id или service_type_id.",
            )
        )

    buffers = await user_project_service.get_buffers_by_scenario_id(
        scenario_id,
        buffer_type_id,
        physical_object_type_id,
        service_type_id,
        user,
    )

    return await GeoJSONResponse.from_list([buffer.to_geojson_dict() for buffer in buffers])


@projects_mcp.tool(
    name="GetContextBuffers",
    title="Получить зоны ограничений объектов на территории контекста",
    description="""Возвращает зоны ограничений объектов контекста проектной территории текущего сценария в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    buffer_type_id | Optional[int] | нет | Фильтр по типу зоны ограничений.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта. Нельзя использовать одновременно с service_type_id.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса. Нельзя использовать одновременно с physical_object_type_id.
    scenario_id | int | да | Идентификатор сценария в arguments MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioBufferAttributes]] | GeoJSON FeatureCollection с зонами ограничений объектов контекста сценария.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioBufferAttributes:
    Поле | Тип | Описание
    buffer_type | BufferTypeBasic | Тип зоны ограничений, которым построена зона.
    urban_object | ShortUrbanObject | Контекстный городской объект, вокруг которого построена зона ограничений.
    is_custom | bool | Признак пользовательского значения радиуса.
    is_scenario_object | bool | Признак того, что объект относится к сценарию.
    is_locked | bool | Признак блокировки объекта для изменений.
    
    Пример вызова:
    {
      "tool": "GetContextBuffers",
      "arguments": {
        "buffer_type_id": 2,
        "physical_object_type_id": 12
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
            "buffer_type": {"id": 2, "name": "Санитарно-защитная зона"},
            "urban_object": {"id": 30, "name": "Промышленный объект"},
            "is_custom": false,
            "is_scenario_object": false,
            "is_locked": false
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: одновременно переданы physical_object_type_id и service_type_id.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту.
    - -32001 Not found: сценарий, тип зоны ограничений, тип физического объекта или тип сервиса не найдены.
    """,
    tags=["buffers", "context"],
    annotations={"title": "GetContextBuffers", "readOnlyHint": True},
)
async def get_context_buffers(
    scenario_id: Annotated[int, "Идентификатор сценария"],
    buffer_type_id: Annotated[Optional[int], "Фильтр по типу зоны ограничений"] = None,
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    request: Request = CurrentRequest(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioBufferAttributes]]:
    """Get context buffers for a scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service

    if physical_object_type_id is not None and service_type_id is not None:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Укажите только один фильтр: physical_object_type_id или service_type_id.",
            )
        )

    buffers = await user_project_service.get_context_buffers(
        scenario_id,
        buffer_type_id,
        physical_object_type_id,
        service_type_id,
        user,
    )

    return await GeoJSONResponse.from_list([buffer.to_geojson_dict() for buffer in buffers])
