"""MCP tools for projects and scenarios are defined here."""

from fastmcp import Context
from fastmcp.dependencies import CurrentRequest, Depends
from fastmcp.server.dependencies import CurrentContext
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.schemas import (
    Project,
    ProjectCadastreAttributes,
    ProjectPhases,
    ProjectTerritory,
    Scenario,
)
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import projects_scenarios_mcp as projects_mcp


def _get_project_id(context: Context) -> int:
    try:
        return int(context.request_context.meta.project_id)
    except Exception as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="В metadata MCP-запроса отсутствует корректный целочисленный project_id.",
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


@projects_mcp.tool(
    name="GetProjectById",
    title="Получить проект по идентификатору",
    description="""Возвращает карточку проекта по его идентификатору с базовым сценарием, территорией и пользовательскими свойствами.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    metadata.project_id | int | да | Идентификатор проекта в metadata MCP-запроса.
    
    Выходные данные:
    Project | Карточка проекта.
    
    Поля модели:
    Project:
    Поле | Тип | Описание
    project_id | int | Идентификатор проекта.
    user_id | str | Идентификатор пользователя, создавшего проект.
    name | str | Название проекта.
    territory | ShortTerritory | Территория или регион проекта.
    base_scenario | ShortScenario | None | Базовый сценарий проекта, если он задан.
    description | str | None | Описание проекта.
    public | bool | Признак публичного доступа к проекту.
    is_regional | bool | Признак регионального проекта.
    is_city | bool | Признак городского проекта.
    properties | dict | Дополнительные свойства проекта.
    created_at | datetime | Дата и время создания проекта.
    updated_at | datetime | Дата и время последнего обновления проекта.
    
    Пример вызова:
    {
      "tool": "GetProjectById",
      "arguments": {}
    }
    
    Пример результата:
    {
      "project_id": 1,
      "user_id": "planner@example.com",
      "name": "Редевелопмент промзоны",
      "territory": {"id": 10, "name": "Пермь"},
      "base_scenario": {"id": 5, "name": "Базовый сценарий"},
      "description": "Проект комплексного развития территории",
      "public": false,
      "is_regional": false,
      "is_city": true,
      "properties": {},
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.project_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к проекту.
    - -32001 Not found: проект с указанным project_id не найден.
    """,
    tags=["projects"],
    annotations={"title": "GetProjectById", "readOnlyHint": True},
)
async def get_project_by_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> Project:
    """Get project by identifier."""
    user_project_service: UserProjectService = request.state.user_project_service
    project_id = _get_project_id(context)
    project_dto = await user_project_service.get_project_by_id(project_id, user)
    return Project.from_dto(project_dto)


@projects_mcp.tool(
    name="GetProjectTerritoryByProjectId",
    title="Получить территорию проекта",
    description="""Возвращает проектную территорию указанного проекта с геометрией, центром и свойствами.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    metadata.project_id | int | да | Идентификатор проекта в metadata MCP-запроса.
    
    Выходные данные:
    ProjectTerritory | Проектная территория с геометрией.
    
    Поля модели:
    ProjectTerritory:
    Поле | Тип | Описание
    project_territory_id | int | Идентификатор проектной территории.
    project | ShortProjectWithScenario | Краткая карточка проекта с базовым сценарием.
    geometry | Geometry | Геометрия проектной территории.
    centre_point | Point | None | Центр проектной территории.
    properties | dict | Дополнительные свойства проектной территории.
    
    Пример вызова:
    {
      "tool": "GetProjectTerritoryByProjectId",
      "arguments": {}
    }
    
    Пример результата:
    {
      "project_territory_id": 100,
      "project": {"project_id": 1, "user_id": "planner@example.com", "name": "Редевелопмент промзоны", "region": {"id": 10, "name": "Пермь"}, "base_scenario": {"id": 5, "name": "Базовый сценарий"}},
      "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
      "centre_point": {"type": "Point", "coordinates": [56.25, 58.03]},
      "properties": {"area_ha": 120.5}
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.project_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к проекту.
    - -32001 Not found: проект или проектная территория не найдены.
    """,
    tags=["projects", "territories"],
    annotations={"title": "GetProjectTerritoryByProjectId", "readOnlyHint": True},
)
async def get_project_territory_by_project_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> ProjectTerritory:
    """Get territory of project."""
    user_project_service: UserProjectService = request.state.user_project_service
    project_id = _get_project_id(context)
    project_territory_dto = await user_project_service.get_project_territory_by_id(project_id, user)
    return ProjectTerritory.from_dto(project_territory_dto)


@projects_mcp.tool(
    name="GetProjectPhasesByProjectId",
    title="Получить фазы проекта",
    description="""Возвращает календарные даты и процент выполнения фаз указанного проекта.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    metadata.project_id | int | да | Идентификатор проекта в metadata MCP-запроса.
    
    Выходные данные:
    ProjectPhases | Даты и прогресс фаз проекта.
    
    Поля модели:
    ProjectPhases:
    Поле | Тип | Описание
    actual_start_date | date | None | Фактическая дата начала проекта.
    actual_end_date | date | None | Фактическая дата завершения проекта.
    planned_start_date | date | None | Плановая дата начала проекта.
    planned_end_date | date | None | Плановая дата завершения проекта.
    investment | float | Процент выполнения инвестиционной фазы.
    pre_design | float | Процент выполнения предпроектной фазы.
    design | float | Процент выполнения проектирования.
    construction | float | Процент выполнения строительства.
    operation | float | Процент выполнения эксплуатации.
    decommission | float | Процент выполнения вывода из эксплуатации.
    properties | dict | Дополнительные свойства фаз проекта.
    
    Пример вызова:
    {
      "tool": "GetProjectPhasesByProjectId",
      "arguments": {}
    }
    
    Пример результата:
    {
      "actual_start_date": "2024-01-15",
      "actual_end_date": null,
      "planned_start_date": "2024-01-01",
      "planned_end_date": "2028-12-31",
      "investment": 100.0,
      "pre_design": 80.0,
      "design": 40.0,
      "construction": 0.0,
      "operation": 0.0,
      "decommission": 0.0,
      "properties": {}
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.project_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к проекту.
    - -32001 Not found: проект или данные фаз проекта не найдены.
    """,
    tags=["projects"],
    annotations={"title": "GetProjectPhasesByProjectId", "readOnlyHint": True},
)
async def get_phases_by_project_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> ProjectPhases:
    """Get phases of project."""
    user_project_service: UserProjectService = request.state.user_project_service
    project_id = _get_project_id(context)
    project_phases_dto = await user_project_service.get_project_phases_by_id(project_id, user)
    return ProjectPhases.from_dto(project_phases_dto)


@projects_mcp.tool(
    name="GetProjectCadastresByProjectId",
    title="Получить кадастровые участки проекта",
    description="""Возвращает кадастровые участки, пересекающиеся с проектной территорией, в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    metadata.project_id | int | да | Идентификатор проекта в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, ProjectCadastreAttributes]] | GeoJSON FeatureCollection с кадастровыми участками проекта.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    ProjectCadastreAttributes:
    Поле | Тип | Описание
    project_cadastre_id | int | Идентификатор кадастрового участка проекта.
    properties | dict | Дополнительные свойства кадастрового участка.
    area | float | None | Площадь участка.
    cad_num | str | None | Кадастровый номер участка.
    cost_value | float | None | Кадастровая стоимость.
    land_record_area | float | None | Учетная площадь земельного участка.
    land_record_category_type | str | None | Категория земель.
    ownership_type | str | None | Вид собственности.
    permitted_use_established_by_document | str | None | Разрешенное использование по документу.
    quarter_cad_number | str | None | Кадастровый номер квартала.
    readable_address | str | None | Читаемый адрес участка.
    specified_area | float | None | Уточненная площадь.
    status | str | None | Статус кадастровой записи.
    zone_pzz | str | None | Территориальная зона ПЗЗ.
    possible_pzz_vri | str | None | Возможный ВРИ по ПЗЗ.
    possible_vri_list | str | None | Список возможных видов разрешенного использования.
    similarity_score | float | None | Оценка схожести участка с проектной территорией.
    
    Пример вызова:
    {
      "tool": "GetProjectCadastresByProjectId",
      "arguments": {}
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.21, 58.0], [56.21, 58.01], [56.2, 58.0]]]},
          "properties": {
            "project_cadastre_id": 77,
            "cad_num": "59:01:0000000:123",
            "area": 1250.5,
            "cost_value": 1500000.0,
            "readable_address": "г. Пермь, ул. Ленина, 1",
            "similarity_score": 0.92,
            "properties": {}
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.project_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к проекту.
    - -32001 Not found: проект или кадастровые участки проектной территории не найдены.
    """,
    tags=["projects", "cadastres"],
    annotations={"title": "GetProjectCadastresByProjectId", "readOnlyHint": True},
)
async def get_cadastres_by_project_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ProjectCadastreAttributes]]:
    """Get cadastres of project in GeoJSON format."""
    user_project_service: UserProjectService = request.state.user_project_service
    project_id = _get_project_id(context)
    cadastres = await user_project_service.get_cadastres(project_id, user)
    return await GeoJSONResponse.from_list([cadastre.to_geojson_dict() for cadastre in cadastres])


@projects_mcp.tool(
    name="GetScenarioById",
    title="Получить сценарий по идентификатору",
    description="""Возвращает карточку сценария по его идентификатору с проектом, родительским сценарием и целевым профилем функционального зонирования.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    Scenario | Карточка сценария.
    
    Поля модели:
    Scenario:
    Поле | Тип | Описание
    scenario_id | int | Идентификатор сценария.
    parent_scenario | ShortScenario | None | Родительский сценарий, если сценарий создан как копия другого.
    project | ShortProject | Проект, которому принадлежит сценарий.
    functional_zone_type | FunctionalZoneTypeBasic | None | Целевой профиль функционального зонирования сценария.
    name | str | Название сценария.
    is_based | bool | Признак базового сценария проекта.
    properties | dict | Дополнительные свойства сценария.
    created_at | datetime | Дата и время создания сценария.
    updated_at | datetime | Дата и время последнего обновления сценария.
    
    Пример вызова:
    {
      "tool": "GetScenarioById",
      "arguments": {}
    }
    
    Пример результата:
    {
      "scenario_id": 5,
      "parent_scenario": null,
      "project": {"project_id": 1, "user_id": "planner@example.com", "name": "Редевелопмент промзоны", "region": {"id": 10, "name": "Пермь"}},
      "functional_zone_type": {"id": 3, "name": "Жилая зона", "nickname": "J", "description": "Преобладающая жилая застройка"},
      "name": "Базовый сценарий",
      "is_based": true,
      "properties": {},
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий с указанным scenario_id не найден.
    """,
    tags=["projects", "scenarios"],
    annotations={"title": "GetScenarioById", "readOnlyHint": True},
)
async def get_scenario_by_id(
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> Scenario:
    """Get scenario by identifier."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    scenario = await user_project_service.get_scenario_by_id(scenario_id, user)
    return Scenario.from_dto(scenario)
