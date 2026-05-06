"""MCP tools for functional zones are defined here."""

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
from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    FunctionalZone,
    FunctionalZoneSource,
    FunctionalZoneWithoutGeometry,
    ScenarioFunctionalZoneWithoutGeometry,
)
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_mcp.dependencies import auth_dep
from idu_api.urban_mcp.handlers.routers import functional_zones_mcp


@functional_zones_mcp.tool(
    name="GetFunctionalZoneSources",
    title="Получить источники функциональных зон",
    description="""Возвращает доступные пары года и источника данных функциональных зон для указанной территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, для которой нужно найти доступные наборы функционального зонирования.
    include_child_territories | bool | нет | Если true, источники собираются также по дочерним территориям.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    list[FunctionalZoneSource] | Список доступных источников функциональных зон с годами данных.
    
    Поля модели:
    FunctionalZoneSource:
    Поле | Тип | Описание
    year | int | Год, к которому относится набор функциональных зон.
    source | str | Название источника данных функционального зонирования.
    
    Пример вызова:
    {
      "tool": "GetFunctionalZoneSources",
      "arguments": {
        "territory_id": 1,
        "include_child_territories": true,
        "cities_only": false
      }
    }
    
    Пример результата:
    [
      {"year": 2024, "source": "Генеральный план"}
    ]
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория не найдена или для нее нет доступных источников функциональных зон.
    """,
    tags=["territories", "functional_zones"],
    annotations={"title": "GetFunctionalZoneSources", "readOnlyHint": True},
)
async def get_functional_zone_sources(
    territory_id: Annotated[int, "Идентификатор территории"],
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Только города"] = False,
    request: Request = CurrentRequest(),
) -> list[FunctionalZoneSource]:
    """Get sources of functional zones for a given territory."""
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )

    sources = await territories_service.get_functional_zones_sources_by_territory_id(
        territory_id,
        include_child_territories,
        cities_only,
    )

    return [FunctionalZoneSource.from_dto(source) for source in sources]


@functional_zones_mcp.tool(
    name="GetFunctionalZones",
    title="Получить функциональные зоны",
    description="""Возвращает функциональные зоны указанной территории за выбранный год и источник в виде списка объектов с геометрией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, по которой нужно получить функциональные зоны.
    year | int | да | Год набора функционального зонирования.
    source | str | да | Источник данных функционального зонирования.
    functional_zone_type_id | Optional[int] | нет | Фильтр по идентификатору типа функциональной зоны.
    include_child_territories | bool | нет | Если true, в выдачу включаются зоны дочерних территорий.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    list[FunctionalZone] | Список функциональных зон с геометрией и атрибутами.
    
    Поля модели:
    FunctionalZone:
    Поле | Тип | Описание
    functional_zone_id | int | Идентификатор функциональной зоны.
    territory | ShortTerritory | Краткое описание территории, к которой относится зона.
    functional_zone_type | FunctionalZoneTypeBasic | Тип функциональной зоны.
    name | str | None | Название зоны, если оно задано в источнике.
    geometry | Geometry | Геометрия зоны.
    year | int | Год набора функционального зонирования.
    source | str | Источник данных функционального зонирования.
    properties | dict | Дополнительные свойства зоны из источника данных.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetFunctionalZones",
      "arguments": {
        "territory_id": 1,
        "year": 2024,
        "source": "Генеральный план",
        "functional_zone_type_id": 3,
        "include_child_territories": true,
        "cities_only": false
      }
    }
    
    Пример результата:
    [
      {
        "functional_zone_id": 10,
        "territory": {"id": 1, "name": "Пермь"},
        "functional_zone_type": {"id": 3, "name": "Жилая зона"},
        "name": "Зона Ж-1",
        "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
        "year": 2024,
        "source": "Генеральный план",
        "properties": {"zone_code": "Ж-1"},
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория, тип функциональной зоны или набор данных с указанными year/source не найдены.
    """,
    tags=["territories", "functional_zones"],
    annotations={"title": "GetFunctionalZones", "readOnlyHint": True},
)
async def get_functional_zones(
    territory_id: Annotated[int, "Идентификатор территории"],
    year: Annotated[int, "Год загрузки функциональных зон"],
    source: Annotated[str, "Источник функциональных зон"],
    functional_zone_type_id: Annotated[Optional[int], "Фильтр по типу функциональной зоны"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Только города"] = False,
    request: Request = CurrentRequest(),
) -> list[FunctionalZone]:
    """Get functional zones for a given territory."""
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )

    zones = await territories_service.get_functional_zones_by_territory_id(
        territory_id,
        year,
        source,
        functional_zone_type_id,
        include_child_territories,
        cities_only,
    )

    return [FunctionalZone.from_dto(zone) for zone in zones]


@functional_zones_mcp.tool(
    name="GetFunctionalZonesGeoJSON",
    title="Получить функциональные зоны в формате GeoJSON",
    description="""Возвращает функциональные зоны указанной территории за выбранный год и источник в формате GeoJSON FeatureCollection.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, по которой нужно получить функциональные зоны.
    year | int | да | Год набора функционального зонирования.
    source | str | да | Источник данных функционального зонирования.
    functional_zone_type_id | Optional[int] | нет | Фильтр по идентификатору типа функциональной зоны.
    include_child_territories | bool | нет | Если true, в выдачу включаются зоны дочерних территорий.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, FunctionalZoneWithoutGeometry]] | GeoJSON FeatureCollection с геометрией функциональных зон и атрибутами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    FunctionalZoneWithoutGeometry:
    Поле | Тип | Описание
    functional_zone_id | int | Идентификатор функциональной зоны.
    territory | ShortTerritory | Краткое описание территории, к которой относится зона.
    functional_zone_type | FunctionalZoneTypeBasic | Тип функциональной зоны.
    name | str | None | Название зоны, если оно задано в источнике.
    year | int | Год набора функционального зонирования.
    source | str | Источник данных функционального зонирования.
    properties | dict | Дополнительные свойства зоны из источника данных.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetFunctionalZonesGeoJSON",
      "arguments": {
        "territory_id": 1,
        "year": 2024,
        "source": "Генеральный план",
        "functional_zone_type_id": 3
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
          "properties": {
            "functional_zone_id": 10,
            "territory": {"id": 1, "name": "Пермь"},
            "functional_zone_type": {"id": 3, "name": "Жилая зона"},
            "name": "Зона Ж-1",
            "year": 2024,
            "source": "Генеральный план",
            "properties": {"zone_code": "Ж-1"}
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория, тип функциональной зоны или набор данных с указанными year/source не найдены.
    """,
    tags=["territories", "functional_zones"],
    annotations={"title": "GetFunctionalZonesGeoJSON", "readOnlyHint": True},
)
async def get_functional_zones_geojson(
    territory_id: Annotated[int, "Идентификатор территории"],
    year: Annotated[int, "Год загрузки функциональных зон"],
    source: Annotated[str, "Источник функциональных зон"],
    functional_zone_type_id: Annotated[Optional[int], "Фильтр по типу функциональной зоны"] = None,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = True,
    cities_only: Annotated[bool, "Только города"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, FunctionalZoneWithoutGeometry]]:
    """Get functional zones in GeoJSON format for a given territory."""
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )

    zones = await territories_service.get_functional_zones_by_territory_id(
        territory_id,
        year,
        source,
        functional_zone_type_id,
        include_child_territories,
        cities_only,
    )

    return await GeoJSONResponse.from_list([zone.to_geojson_dict() for zone in zones])


@functional_zones_mcp.tool(
    name="GetScenarioFunctionalZoneSources",
    title="Получить источники функциональных зон сценария",
    description="""Возвращает доступные пары года и источника данных функциональных зон для текущего сценария.
    Входные параметры:
    отсутствуют; идентификатор сценария берется из metadata.scenario_id MCP-запроса.
    
    Выходные данные:
    list[FunctionalZoneSource] | Список доступных источников функциональных зон сценария с годами данных.
    
    Поля модели:
    FunctionalZoneSource:
    Поле | Тип | Описание
    year | int | Год, к которому относится набор функциональных зон сценария.
    source | str | Название источника данных функционального зонирования.
    
    Пример вызова:
    {
      "tool": "GetScenarioFunctionalZoneSources",
      "arguments": {}
    }
    
    Пример результата:
    [
      {"year": 2024, "source": "Проектный сценарий"}
    ]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий не найден или для него нет доступных источников функциональных зон.
    """,
    tags=["functional_zones", "scenarios"],
    annotations={"title": "GetScenarioFunctionalZoneSources", "readOnlyHint": True},
)
async def get_functional_zone_sources_by_scenario_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[FunctionalZoneSource]:
    """Get functional zone sources for the current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service

    try:
        scenario_id = int(context.request_context.meta.scenario_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный scenario_id.",
            )
        ) from exc

    sources = await user_project_service.get_functional_zones_sources_by_scenario_id(scenario_id, user)

    return [FunctionalZoneSource.from_dto(source) for source in sources]


@functional_zones_mcp.tool(
    name="GetScenarioFunctionalZones",
    title="Получить функциональные зоны сценария",
    description="""Возвращает функциональные зоны проектной территории текущего сценария в формате GeoJSON FeatureCollection.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    year | int | да | Год набора функционального зонирования сценария.
    source | str | да | Источник данных функционального зонирования сценария.
    functional_zone_type_id | Optional[int] | нет | Фильтр по идентификатору типа функциональной зоны.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ScenarioFunctionalZoneWithoutGeometry]] | GeoJSON FeatureCollection с геометрией функциональных зон сценария и атрибутами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ScenarioFunctionalZoneWithoutGeometry:
    Поле | Тип | Описание
    functional_zone_id | int | Идентификатор функциональной зоны сценария.
    functional_zone_type | FunctionalZoneTypeBasic | Тип функциональной зоны.
    name | str | None | Название зоны, если оно задано в источнике.
    year | int | Год набора функционального зонирования.
    source | str | Источник данных функционального зонирования.
    properties | dict | Дополнительные свойства зоны из источника данных.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetScenarioFunctionalZones",
      "arguments": {
        "year": 2024,
        "source": "Проектный сценарий",
        "functional_zone_type_id": 3
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
          "properties": {
            "functional_zone_id": 15,
            "functional_zone_type": {"id": 3, "name": "Жилая зона"},
            "name": "Проектная зона Ж-1",
            "year": 2024,
            "source": "Проектный сценарий",
            "properties": {"zone_code": "Ж-1"}
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, тип функциональной зоны или набор данных с указанными year/source не найдены.
    """,
    tags=["functional_zones", "scenarios"],
    annotations={"title": "GetScenarioFunctionalZones", "readOnlyHint": True},
)
async def get_functional_zones_by_scenario_id(
    year: Annotated[int, "Год загрузки функциональных зон"],
    source: Annotated[str, "Источник функциональных зон"],
    functional_zone_type_id: Annotated[Optional[int], "Фильтр по типу функциональной зоны"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ScenarioFunctionalZoneWithoutGeometry]]:
    """Get functional zones for the current scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service

    try:
        scenario_id = int(context.request_context.meta.scenario_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный scenario_id.",
            )
        ) from exc

    functional_zones = await user_project_service.get_functional_zones_by_scenario_id(
        scenario_id, year, source, functional_zone_type_id, user
    )

    return await GeoJSONResponse.from_list([zone.to_geojson_dict() for zone in functional_zones])


@functional_zones_mcp.tool(
    name="GetContextFunctionalZoneSources",
    title="Получить источники функциональных зон контекста",
    description="""Возвращает доступные пары года и источника данных функциональных зон контекста текущего сценария.
    Входные параметры:
    отсутствуют; идентификатор сценария берется из metadata.scenario_id MCP-запроса.
    
    Выходные данные:
    list[FunctionalZoneSource] | Список доступных источников контекстных функциональных зон с годами данных.
    
    Поля модели:
    FunctionalZoneSource:
    Поле | Тип | Описание
    year | int | Год, к которому относится набор контекстных функциональных зон.
    source | str | Название источника данных функционального зонирования.
    
    Пример вызова:
    {
      "tool": "GetContextFunctionalZoneSources",
      "arguments": {}
    }
    
    Пример результата:
    [
      {"year": 2024, "source": "Генеральный план"}
    ]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий не найден или для его контекста нет доступных источников функциональных зон.
    """,
    tags=["functional_zones", "scenarios", "context"],
    annotations={"title": "GetContextFunctionalZoneSources", "readOnlyHint": True},
)
async def get_context_functional_zone_sources(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[FunctionalZoneSource]:
    """Get context functional zone sources for the current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service

    try:
        scenario_id = int(context.request_context.meta.scenario_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный scenario_id.",
            )
        ) from exc

    sources = await user_project_service.get_context_functional_zones_sources(scenario_id, user)

    return [FunctionalZoneSource.from_dto(source) for source in sources]


@functional_zones_mcp.tool(
    name="GetContextFunctionalZones",
    title="Получить функциональные зоны контекста",
    description="""Возвращает функциональные зоны контекста текущего сценария в формате GeoJSON FeatureCollection.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    year | int | да | Год набора контекстного функционального зонирования.
    source | str | да | Источник данных контекстного функционального зонирования.
    functional_zone_type_id | Optional[int] | нет | Фильтр по идентификатору типа функциональной зоны.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, FunctionalZoneWithoutGeometry]] | GeoJSON FeatureCollection с геометрией контекстных функциональных зон и атрибутами в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    FunctionalZoneWithoutGeometry:
    Поле | Тип | Описание
    functional_zone_id | int | Идентификатор контекстной функциональной зоны.
    territory | ShortTerritory | Краткое описание территории, к которой относится зона.
    functional_zone_type | FunctionalZoneTypeBasic | Тип функциональной зоны.
    name | str | None | Название зоны, если оно задано в источнике.
    year | int | Год набора функционального зонирования.
    source | str | Источник данных функционального зонирования.
    properties | dict | Дополнительные свойства зоны из источника данных.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetContextFunctionalZones",
      "arguments": {
        "year": 2024,
        "source": "Генеральный план",
        "functional_zone_type_id": 3
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
          "properties": {
            "functional_zone_id": 10,
            "territory": {"id": 1, "name": "Пермь"},
            "functional_zone_type": {"id": 3, "name": "Жилая зона"},
            "name": "Зона Ж-1",
            "year": 2024,
            "source": "Генеральный план",
            "properties": {"zone_code": "Ж-1"}
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, тип функциональной зоны или контекстный набор данных с указанными year/source не найдены.
    """,
    tags=["functional_zones", "scenarios", "context"],
    annotations={"title": "GetContextFunctionalZones", "readOnlyHint": True},
)
async def get_context_functional_zones(
    year: Annotated[int, "Год загрузки функциональных зон"],
    source: Annotated[str, "Источник функциональных зон"],
    functional_zone_type_id: Annotated[Optional[int], "Фильтр по типу функциональной зоны"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, FunctionalZoneWithoutGeometry]]:
    """Get context functional zones for the current scenario in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service

    try:
        scenario_id = int(context.request_context.meta.scenario_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный scenario_id.",
            )
        ) from exc

    functional_zones = await user_project_service.get_context_functional_zones(
        scenario_id, year, source, functional_zone_type_id, user
    )

    return await GeoJSONResponse.from_list([zone.to_geojson_dict() for zone in functional_zones])
