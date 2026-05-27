"""MCP tools for territories are defined here."""

from datetime import date
from typing import Annotated, Optional

from fastmcp.dependencies import CurrentRequest
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    TargetCityType,
    Territory,
    TerritoryTreeWithoutGeometry,
    TerritoryType,
    TerritoryWithNormatives,
    TerritoryWithoutGeometry,
)
from idu_api.urban_api.schemas.enums import OrderByField, Ordering
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from idu_api.urban_api.schemas.normatives import Normative
from idu_api.urban_api.schemas.pages import MCPCursorPage, MCPCursorParams

from .routers import dictionaries_mcp, territories_mcp


def _parse_ids(ids: str) -> list[int]:
    try:
        return list({int(tid.strip()) for tid in ids.split(",")})
    except ValueError as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр territories_ids должен быть строкой с целочисленными идентификаторами территорий, перечисленными через запятую.",
            )
        ) from exc


def _validate_levels(get_all_levels: bool, cities_only: bool) -> None:
    if not get_all_levels and cities_only:
        raise McpError(
            ErrorData(code=-32602, message="Параметр cities_only можно использовать только при get_all_levels=true.")
        )


def _validate_normatives_year(year: int | None, last_only: bool) -> None:
    if year is not None and last_only:
        raise McpError(ErrorData(code=-32602, message="Параметры year и last_only нельзя использовать одновременно."))


@territories_mcp.tool(
    name="GetTerritoryById",
    title="Получить территорию по идентификатору",
    description="""Возвращает территорию по её идентификатору вместе с геометрией, административными атрибутами и служебной информацией.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    
    Выходные данные:
    Territory | Территория с геометрией и полным набором атрибутов.
    
    Поля модели:
    Territory:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория, если она есть.
    name | str | Название территории.
    geometry | Geometry | Геометрия территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства территории.
    centre_point | Point | Географический центр территории.
    admin_center | ShortTerritory | None | Административный центр территории.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города, если территория является городом с заданным статусом.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак того, что территория является городом.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetTerritoryById",
      "arguments": {
        "territory_id": 1
      }
    }
    
    Пример результата:
    {
      "territory_id": 1,
      "name": "Санкт-Петербург",
      "level": 2,
      "is_city": true
    }
    
    Ошибки:
    - -32001 Not found: территория с указанным territory_id не найдена.
    """,
    tags=["territories"],
    annotations={"title": "GetTerritoryById", "readOnlyHint": True},
)
async def get_territory_by_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    request: Request = CurrentRequest(),
) -> Territory:
    """Get a territory by identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    territory = await territories_service.get_territory_by_id(territory_id)
    return Territory.from_dto(territory)


@territories_mcp.tool(
    name="GetAllTerritoriesGeoJSON",
    title="Получить все территории в формате GeoJSON",
    description="""Возвращает территории в формате GeoJSON FeatureCollection с возможностью фильтрации по родительской территории, типу, названию, дате создания и признаку города.

    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, возвращаются территории верхнего уровня.
    get_all_levels | bool | нет | Если true, возвращаются территории из всего поддерева parent_id.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории.
    name | Optional[str] | нет | Фильтр по подстроке названия без учета регистра.
    cities_only | bool | нет | Если true, возвращаются только города. Допустимо только при get_all_levels=true.
    created_at | Optional[date] | нет | Фильтр по дате создания территории.
    centers_only | bool | нет | Если true, вместо полной геометрии территории возвращается точка центра.

    Выходные данные:
    GeoJSONResponse[Feature[Geometry, TerritoryWithoutGeometry]] | GeoJSON FeatureCollection, где geometry содержит геометрию территории или её центр, а properties содержит атрибуты территории без geometry.

    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции. Всегда FeatureCollection.
    features | list[Feature] | Список GeoJSON Feature.

    Feature:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-объекта. Всегда Feature.
    geometry | Geometry | Геометрия территории или центр территории при centers_only=true.
    properties | TerritoryWithoutGeometry | Атрибуты территории без geometry.

    Пример вызова:
    {
      "tool": "GetAllTerritoriesGeoJSON",
      "arguments": {
        "parent_id": 1,
        "get_all_levels": true,
        "cities_only": true,
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
            "territory_id": 2,
            "name": "Санкт-Петербург",
            "is_city": true
          }
        }
      ]
    }

    Ошибки:
    - -32602 Invalid params: cities_only=true передан при get_all_levels=false.
    - -32001 Not found: parent_id или territory_type_id не найден.
    """,
    tags=["territories"],
    annotations={"title": "GetAllTerritoriesGeoJSON", "readOnlyHint": True},
)
async def get_all_territories_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    get_all_levels: Annotated[bool, "Возвращать всё поддерево территорий"] = False,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    name: Annotated[Optional[str], "Фильтр по названию территории (подстрока)"] = None,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    created_at: Annotated[Optional[date], "Фильтр по дате создания территории"] = None,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithoutGeometry]]:
    """Get all territories by parent identifier as GeoJSON."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_levels(get_all_levels, cities_only)
    territories = await territories_service.get_territories_by_parent_id(
        parent_id, get_all_levels, territory_type_id, name, cities_only, created_at, None, "asc", paginate=False
    )
    return await GeoJSONResponse.from_list([territory.to_geojson_dict() for territory in territories], centers_only)


@territories_mcp.tool(
    name="GetAllTerritoriesWithoutGeometry",
    title="Получить все территории без геометрии",
    description="""Возвращает список всех территорий без геометрий с возможностью фильтрации по родительской территории, типу, названию, дате создания и признаку города.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, возвращаются территории верхнего уровня.
    get_all_levels | bool | нет | Если true, возвращаются территории из всего поддерева parent_id. Если false, возвращаются только непосредственные дочерние территории.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории.
    name | Optional[str] | нет | Фильтр по подстроке названия без учета регистра.
    cities_only | bool | нет | Если true, возвращаются только города. Допустимо только при get_all_levels=true.
    created_at | Optional[date] | нет | Фильтр по дате создания территории.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки: asc или desc.

    Выходные данные:
    list[TerritoryWithoutGeometry] | Список территорий без геометрии.

    Поля модели:
    TerritoryWithoutGeometry:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория.
    name | str | Название территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства.
    centre_point | Point | Географический центр территории.
    admin_center | ShortTerritory | None | Административный центр.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак города.
    created_at | datetime | Дата создания записи.
    updated_at | datetime | Дата обновления записи.

    Пример вызова:
    {
      "tool": "GetAllTerritoriesWithoutGeometry",
      "arguments": {
        "parent_id": 1,
        "get_all_levels": true,
        "cities_only": true,
        "ordering": "asc"
      }
    }

    Пример результата:
    {
      "territory_id": 2,
      "name": "Санкт-Петербург",
      "level": 2,
      "is_city": true
    }
  ]

    Ошибки:
    - -32602 Invalid params: cities_only=true передан при get_all_levels=false.
    - -32001 Not found: parent_id или territory_type_id не найден.
    """,
    tags=["territories", "without_geometry"],
    annotations={"title": "GetAllTerritoriesWithoutGeometry", "readOnlyHint": True},
)
async def get_all_territories_without_geometry_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    get_all_levels: Annotated[bool, "Возвращать всё поддерево территорий"] = False,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    name: Annotated[Optional[str], "Фильтр по названию территории (подстрока)"] = None,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    created_at: Annotated[Optional[date], "Фильтр по дате создания территории"] = None,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    request: Request = CurrentRequest(),
) -> list[TerritoryWithoutGeometry]:
    """Get all territories without geometry by parent identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_levels(get_all_levels, cities_only)
    territories = await territories_service.get_territories_without_geometry_by_parent_id(
        parent_id,
        get_all_levels,
        territory_type_id,
        name,
        cities_only,
        created_at,
        order_by.value if order_by is not None else None,
        ordering.value,
        paginate=False,
    )
    return [TerritoryWithoutGeometry.from_dto(territory) for territory in territories]


@territories_mcp.tool(
    name="GetTerritoriesWithoutGeometryHierarchy",
    title="Получить иерархию территорий без геометрии",
    description="""Возвращает иерархическое дерево территорий без геометрии, начиная с указанной родительской территории.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, возвращаются деревья территорий верхнего уровня.
    order_by | Optional[OrderByField] | нет | Поле сортировки территорий внутри каждого уровня иерархии.
    ordering | Ordering | нет | Направление сортировки: asc или desc.

    Выходные данные:
    list[TerritoryTreeWithoutGeometry] | Иерархическое дерево территорий без поля geometry.

    Поля модели:
    TerritoryTreeWithoutGeometry:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория.
    name | str | Название территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства территории.
    admin_center | ShortTerritory | None | Административный центр территории.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак того, что территория является городом.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    children | list[TerritoryTreeWithoutGeometry] | Дочерние территории текущего узла дерева.

    Пример вызова:
    {
      "tool": "GetTerritoriesWithoutGeometryHierarchy",
      "arguments": {
        "parent_id": 1,
        "order_by": "created_at",
        "ordering": "asc"
      }
    }

    Пример результата:
    [
      {
        "territory_id": 1,
        "name": "Российская Федерация",
        "level": 1,
        "children": [
          {
            "territory_id": 2,
            "name": "Санкт-Петербург",
            "level": 2,
            "children": []
          }
        ]
      }
    ]

    Ошибки:
    - -32001 Not found: parent_id не найден.
    """,
    tags=["territories", "without_geometry"],
    annotations={"title": "GetTerritoriesWithoutGeometryHierarchy", "readOnlyHint": True},
)
async def get_all_territories_without_geometry_hierarchy(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    request: Request = CurrentRequest(),
) -> list[TerritoryTreeWithoutGeometry]:
    """Get territories without a geometry hierarchy."""
    territories_service: TerritoriesService = request.state.territories_service
    territories_trees = await territories_service.get_territories_trees_without_geometry_by_parent_id(
        parent_id, order_by.value if order_by is not None else None, ordering.value
    )
    return [TerritoryTreeWithoutGeometry.from_dto(territories_tree) for territories_tree in territories_trees]


@territories_mcp.tool(
    name="GetTerritoriesByIdsGeoJSON",
    title="Получить территории по идентификаторам в формате GeoJSON",
    description="""Возвращает указанные территории в формате GeoJSON FeatureCollection по списку идентификаторов.

    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territories_ids | str | да | Идентификаторы территорий, перечисленные через запятую. Пример: "1,2,3".
    centers_only | bool | нет | Если true, вместо полной геометрии каждой территории возвращается точка центра.

    Выходные данные:
    GeoJSONResponse[Feature[Geometry, TerritoryWithoutGeometry]] | GeoJSON FeatureCollection, где geometry содержит геометрию территории или её центр, а properties содержит атрибуты территории без geometry.

    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции. Всегда FeatureCollection.
    features | list[Feature] | Список GeoJSON Feature.

    Feature:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-объекта. Всегда Feature.
    geometry | Geometry | Геометрия территории или центр территории при centers_only=true.
    properties | TerritoryWithoutGeometry | Атрибуты территории без geometry.

    TerritoryWithoutGeometry:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория.
    name | str | Название территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства территории.
    admin_center | ShortTerritory | None | Административный центр территории.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак того, что территория является городом.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.

    Пример вызова:
    {
      "tool": "GetTerritoriesByIdsGeoJSON",
      "arguments": {
        "territories_ids": "1,2,3",
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
            "territory_id": 1,
            "name": "Санкт-Петербург",
            "level": 2,
            "is_city": true
          }
        }
      ]
    }

    Ошибки:
    - -32602 Invalid params: territories_ids пустой или содержит нецелочисленные значения.
    - -32001 Not found: одна или несколько территорий из territories_ids не найдены.
    """,
    tags=["territories"],
    annotations={"title": "GetTerritoriesByIdsGeoJSON", "readOnlyHint": True},
)
async def get_territories_by_ids(
    territories_ids: Annotated[str, "Идентификаторы территорий, перечисленные через запятую"],
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithoutGeometry]]:
    """Get territories by identifiers."""
    territories_service: TerritoriesService = request.state.territories_service
    territories = await territories_service.get_territories_by_ids(_parse_ids(territories_ids))
    return await GeoJSONResponse.from_list([t.to_geojson_dict() for t in territories], centers_only=centers_only)


@dictionaries_mcp.tool(
    name="GetTerritoryTypes",
    title="Получить типы территорий",
    description="""Возвращает справочник типов территорий, используемых для классификации территориальных единиц в иерархии.
    Входные параметры:
    отсутствуют

    Выходные данные:
    list[TerritoryType] | Список доступных типов территорий.

    Поля модели:
    TerritoryType:
    Поле | Тип | Описание
    territory_type_id | int | Идентификатор типа территории.
    name | str | Название типа территории.

    Пример вызова:
    {
      "tool": "GetTerritoryTypes",
      "arguments": {}
    }

    Пример результата:
    [
      {
        "territory_type_id": 1,
        "name": "Город"
      }
    ]

    Ошибки:
    - -32001 Not found: справочник типов территорий недоступен или не найден.
    """,
    tags=["territories"],
    annotations={"title": "GetTerritoryTypes", "readOnlyHint": True},
)
async def get_territory_types(request: Request = CurrentRequest()) -> list[TerritoryType]:
    """Get territory types."""
    territories_service: TerritoriesService = request.state.territories_service
    territory_types = await territories_service.get_territory_types()
    return [TerritoryType.from_dto(territory_type) for territory_type in territory_types]


@dictionaries_mcp.tool(
    name="GetTargetCityTypes",
    title="Получить типы целевых городов",
    description="""Возвращает справочник целевых типов городов, используемых для указания статуса города в территориальной структуре.
    Входные параметры:
    отсутствуют

    Выходные данные:
    list[TargetCityType] | Список доступных целевых типов городов.

    Поля модели:
    TargetCityType:
    Поле | Тип | Описание
    target_city_type_id | int | Идентификатор целевого типа города.
    name | str | Название целевого типа города.
    description | str | Описание значения и правил применения целевого типа города.

    Пример вызова:
    {
      "tool": "GetTargetCityTypes",
      "arguments": {}
    }

    Пример результата:
    [
      {
        "target_city_type_id": 1,
        "name": "Административный центр",
        "description": "Статус административного центра субъекта Российской Федерации"
      }
    ]

    Ошибки:
    - -32001 Not found: справочник целевых типов городов недоступен или не найден.
    """,
    tags=["territories"],
    annotations={"title": "GetTargetCityTypes", "readOnlyHint": True},
)
async def get_target_city_types(request: Request = CurrentRequest()) -> list[TargetCityType]:
    """Get target city types."""
    territories_service: TerritoriesService = request.state.territories_service
    target_city_types = await territories_service.get_target_city_types()
    return [TargetCityType.from_dto(target_city_type) for target_city_type in target_city_types]


@territories_mcp.tool(
    name="GetTerritoryNormatives",
    title="Получить нормативы на территории",
    description="""Возвращает нормативы обеспеченности для указанной территории с возможностью получить значения за конкретный год, последние доступные значения или значения по дочерним территориям.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    year | Optional[int] | нет | Год, за который нужно получить нормативы. Нельзя использовать одновременно с last_only=true.
    last_only | bool | нет | Если true, возвращаются только последние доступные нормативы. Нельзя использовать одновременно с year.
    include_child_territories | bool | нет | Если true, возвращаются также дочерние территории.
    cities_only | bool | нет | Если true, возвращаются нормативы только по дочерним территориям-городам. Допустимо только при include_child_territories=true.

    Выходные данные:
    list[Normative] | Список нормативов обеспеченности.

    Поля модели:
    Normative:
    Поле | Тип | Описание
    service_type | ServiceTypeBasic | None | Тип сервиса, к которому относится норматив.
    urban_function | UrbanFunctionBasic | None | Городская функция, к которой относится норматив.
    year | int | Год действия норматива.
    territory | ShortTerritory | Территория, для которой задан норматив.
    radius_availability_meters | int | None | Норматив радиуса доступности в метрах.
    time_availability_minutes | int | None | Норматив временной доступности в минутах.
    services_per_1000_normative | int | None | Норматив количества сервисов на 1000 жителей.
    services_capacity_per_1000_normative | int | None | Норматив мощности сервисов на 1000 жителей.
    normative_type | NormativeType | Тип норматива.
    is_regulated | bool | Признак регулируемого норматива.

    Пример вызова:
    {
      "tool": "GetTerritoryNormatives",
      "arguments": {
        "territory_id": 1,
        "year": 2024,
        "include_child_territories": false
      }
    }

    Пример результата:
    [
      {
        "year": 2024,
        "territory": {"id": 1, "name": "Санкт-Петербург"},
        "radius_availability_meters": 500,
        "time_availability_minutes": null,
        "is_regulated": true
      }
    ]

    Ошибки:
    - -32602 Invalid params: year и last_only=true переданы одновременно.
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: territory_id не найден.
    """,
    tags=["normatives"],
    annotations={"title": "GetTerritoryNormatives", "readOnlyHint": True},
)
async def get_territory_normatives(
    territory_id: Annotated[int, "Идентификатор территории"],
    year: Annotated[Optional[int], "Год действия нормативов"] = None,
    last_only: Annotated[bool, "Возвращать только последние доступные нормативы"] = False,
    include_child_territories: Annotated[bool, "Возвращать дочерние территории"] = False,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    request: Request = CurrentRequest(),
) -> list[Normative]:
    """Get territory normatives."""
    territories_service: TerritoriesService = request.state.territories_service
    if not include_child_territories and cities_only:
        raise McpError(ErrorData(code=-32602, message="Некорректные параметры запроса."))
    _validate_normatives_year(year, last_only)
    normatives = await territories_service.get_normatives_by_territory_id(
        territory_id, year, last_only, include_child_territories, cities_only
    )
    return [Normative.from_dto(normative) for normative in normatives]


@territories_mcp.tool(
    name="GetNormativesValuesGeoJSON",
    title="Получить территории с нормативными значениями в формате GeoJSON",
    description="""Возвращает территории с прикрепленными значениями нормативов в формате GeoJSON FeatureCollection.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, используются территории верхнего уровня.
    year | Optional[int] | нет | Год, за который нужно получить нормативы. Нельзя использовать одновременно с last_only=true.
    last_only | bool | нет | Если true, возвращаются только последние доступные нормативы. Нельзя использовать одновременно с year.
    centers_only | bool | нет | Если true, вместо полной геометрии территории возвращается точка центра.

    Выходные данные:
    GeoJSONResponse[Feature[Geometry, TerritoryWithNormatives]] | GeoJSON FeatureCollection, где properties содержит территорию и список нормативов.

    Поля модели:
    TerritoryWithNormatives:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    name | str | Название территории.
    is_city | bool | Признак города.
    centre_point | Point | Географический центр территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    normatives | list[Normative] | Список нормативов территории.

    Пример вызова:
    {
      "tool": "GetNormativesValuesGeoJSON",
      "arguments": {
        "parent_id": 1,
        "year": 2024,
        "centers_only": true
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
            "territory_id": 2,
            "name": "Санкт-Петербург",
            "normatives": []
          }
        }
      ]
    }

    Ошибки:
    - -32602 Invalid params: year и last_only=true переданы одновременно.
    - -32001 Not found: parent_id не найден.
    """,
    tags=["normatives"],
    annotations={"title": "GetNormativesValuesGeoJSON", "readOnlyHint": True},
)
async def get_normatives_values_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    year: Annotated[Optional[int], "Год действия нормативов"] = None,
    last_only: Annotated[bool, "Возвращать только последние доступные нормативы"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithNormatives]]:
    """Get normatives values by parent territory."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_normatives_year(year, last_only)
    territories = await territories_service.get_normatives_values_by_parent_id(parent_id, year, last_only)
    return await GeoJSONResponse.from_list(
        [territory.to_geojson_dict() for territory in territories], centers_only, save_centers=True
    )


@territories_mcp.tool(
    name="GetTerritories",
    title="Получить страницу территорий",
    description="""Возвращает страницу территорий c поддержкой фильтрации и сортировки.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, возвращаются территории верхнего уровня.
    get_all_levels | bool | нет | Если true, возвращаются территории из всего поддерева parent_id. Если false, возвращаются только непосредственные дочерние территории.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории.
    name | Optional[str] | нет | Фильтр по подстроке названия без учета регистра.
    cities_only | bool | нет | Если true, возвращаются только территории, являющиеся городами. Допустимо только при get_all_levels=true.
    created_at | Optional[date] | нет | Фильтр по дате создания территории.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки: asc или desc.
    cursor | Optional[str] | нет | Курсор для пагинации
    page_size | int | нет | Размер страницы
    
    Выходные данные:
    MCPCursorPage[Territory] | Страница территорий с курсором для получения следующей страницы.

    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list[Territory] | Элементы текущей страницы.
    count | int | Общее количество найденных территорий.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.
    
    Territory:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория.
    name | str | Название территории.
    geometry | Geometry | Геометрия территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства территории.
    centre_point | Point | Географический центр территории.
    admin_center | ShortTerritory | None | Административный центр территории.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак того, что территория является городом.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.

    Пример вызова:
    {
      "tool": "GetTerritories",
      "arguments": {
        "parent_id": 1,
        "get_all_levels": true,
        "cities_only": true,
        "ordering": "asc"
      }
    }

    Пример результата:
    {
      "items": [
        {
          "territory_id": 2,
          "name": "Санкт-Петербург",
          "level": 2,
          "is_city": true
        }
      ],
      "count": 1,
      "page_size": 10,
      "prevCursor": null,
      "nextCursor": "eyJsYXN0X2lkIjoyfQ=="
    }

    Ошибки:
    - -32602 Invalid params: cities_only=true передан при get_all_levels=false.
    - -32001 Not found: parent_id или territory_type_id не найден.
    """,
    tags=["territories"],
    annotations={"title": "GetTerritories", "readOnlyHint": True},
)
async def get_territory_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    get_all_levels: Annotated[bool, "Возвращать всё поддерево территорий"] = False,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    name: Annotated[Optional[str], "Фильтр по названию территории (подстрока)"] = None,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    created_at: Annotated[Optional[date], "Фильтр по дате создания территории"] = None,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[Territory]:
    """Get cursor-base page of territories by parent identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_levels(get_all_levels, cities_only)
    params = MCPCursorParams(cursor=cursor, size=page_size)
    territories = await territories_service.get_territories_by_parent_id(
        parent_id,
        get_all_levels,
        territory_type_id,
        name,
        cities_only,
        created_at,
        order_by.value if order_by is not None else None,
        ordering.value,
        paginate=True,
        params=params,
    )
    return MCPCursorPage.create(
        [Territory.from_dto(item) for item in territories.items],
        params=params,
        total=territories.total,
        **(territories.cursor_data or {}),
    )


@territories_mcp.tool(
    name="GetTerritoriesWithoutGeometry",
    title="Получить страницу территорий без геометрии",
    description="""Возвращает страницу территорий без геометрии, поддержкой фильтрации и сортировки.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории. Если не указан, возвращаются территории верхнего уровня.
    get_all_levels | bool | нет | Если true, возвращаются территории из всего поддерева parent_id. Если false, возвращаются только непосредственные дочерние территории.
    territory_type_id | Optional[int] | нет | Фильтр по типу территории.
    name | Optional[str] | нет | Фильтр по подстроке названия без учета регистра.
    cities_only | bool | нет | Если true, возвращаются только территории, являющиеся городами. Допустимо только при get_all_levels=true.
    created_at | Optional[date] | нет | Фильтр по дате создания территории.
    order_by | Optional[OrderByField] | нет | Поле сортировки.
    ordering | Ordering | нет | Направление сортировки: asc или desc.
    cursor | Optional[str] | нет | Курсор для пагинации
    page_size | int | нет | Размер страницы

    Выходные данные:
    MCPCursorPage[TerritoryWithoutGeometry] | Страница территорий без поля geometry с курсором для получения следующей страницы.

    Поля модели:
    MCPCursorPage:
    Поле | Тип | Описание
    items | list[TerritoryWithoutGeometry] | Элементы текущей страницы.
    count | int | Общее количество найденных территорий.
    page_size | int | Размер страницы
    prevCursor | str | Курсор предыдущей страницы или null, если предыдущей страницы нет.
    nextCursor | str | Курсор следующей страницы или null, если следующей страницы нет.

    TerritoryWithoutGeometry:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    parent | ShortTerritory | None | Родительская территория.
    name | str | Название территории.
    level | int | Уровень территории в иерархии.
    properties | dict[str, Any] | Дополнительные свойства территории.
    admin_center | ShortTerritory | None | Административный центр территории.
    target_city_type | TargetCityTypeBasic | None | Целевой тип города.
    okato_code | str | None | Код ОКАТО.
    oktmo_code | str | None | Код ОКТМО.
    is_city | bool | Признак того, что территория является городом.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.

    Пример вызова:
    {
      "tool": "GetTerritoriesWithoutGeometry",
      "arguments": {
        "parent_id": 1,
        "get_all_levels": true,
        "cities_only": true,
        "ordering": "asc"
      }
    }

    Пример результата:
    {
      "items": [
        {
          "territory_id": 2,
          "name": "Санкт-Петербург",
          "level": 2,
          "is_city": true
        }
      ],
      "count": 1,
      "page_size": 10,
      "prevCursor": null,
      "nextCursor": "eyJsYXN0X2lkIjoyfQ=="
    }

    Ошибки:
    - -32602 Invalid params: cities_only=true передан при get_all_levels=false.
    - -32001 Not found: parent_id или territory_type_id не найден.
    """,
    tags=["territories", "without_geometry"],
    annotations={"title": "GetTerritoriesWithoutGeometry", "readOnlyHint": True},
)
async def get_territory_without_geometry_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    get_all_levels: Annotated[bool, "Возвращать всё поддерево территорий"] = False,
    territory_type_id: Annotated[Optional[int], "Фильтр по типу территории"] = None,
    name: Annotated[Optional[str], "Фильтр по названию территории (подстрока)"] = None,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    created_at: Annotated[Optional[date], "Фильтр по дате создания территории"] = None,
    order_by: Annotated[Optional[OrderByField], "Поле сортировки"] = None,
    ordering: Annotated[Ordering, "Направление сортировки"] = Ordering.ASC,
    cursor: Annotated[Optional[str], "Курсор"] = None,
    page_size: Annotated[int, "Размер страницы"] = 10,
    request: Request = CurrentRequest(),
) -> MCPCursorPage[TerritoryWithoutGeometry]:
    """Get cursor-base page of territories without geometry by parent identifier."""
    territories_service: TerritoriesService = request.state.territories_service
    _validate_levels(get_all_levels, cities_only)
    params = MCPCursorParams(cursor=cursor, size=page_size)
    territories = await territories_service.get_territories_without_geometry_by_parent_id(
        parent_id,
        get_all_levels,
        territory_type_id,
        name,
        cities_only,
        created_at,
        order_by.value if order_by is not None else None,
        ordering.value,
        paginate=True,
        params=params,
    )
    return MCPCursorPage.create(
        [TerritoryWithoutGeometry.from_dto(item) for item in territories.items],
        params=params,
        total=territories.total,
        **(territories.cursor_data or {}),
    )
