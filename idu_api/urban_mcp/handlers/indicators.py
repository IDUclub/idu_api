"""MCP tools for indicators are defined here."""

from datetime import date
from typing import Annotated, Optional

from fastmcp import Context
from fastmcp.dependencies import CurrentRequest, Depends
from fastmcp.server.dependencies import CurrentContext
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.indicators import IndicatorsService
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.logic.territories import TerritoriesService
from idu_api.urban_api.schemas import (
    BinnedIndicatorValue,
    HexagonWithIndicators,
    Indicator,
    IndicatorsGroup,
    IndicatorValue,
    MeasurementUnit,
    ScenarioIndicatorValue,
    ShortTerritoryIndicatorBind,
    TerritoryWithBinnedIndicators,
    TerritoryWithIndicators,
)
from idu_api.urban_api.schemas.enums import DateType, ValueType
from idu_api.urban_api.schemas.geojson import GeoJSONResponse, TerritoriesWithBinnedIndicators
from idu_api.urban_mcp.dependencies import auth_dep

from .routers import indicators_mcp


def _parse_indicator_ids(indicator_ids: str | None) -> set[int] | None:
    if indicator_ids is None:
        return None
    try:
        return {int(ind_id.strip()) for ind_id in indicator_ids.split(",")}
    except ValueError as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр indicator_ids должен быть строкой с целочисленными идентификаторами, разделенными запятыми.",
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


@indicators_mcp.tool(
    name="GetMeasurementUnits",
    title="Получить единицы измерения",
    description="""Возвращает справочник единиц измерения, используемых в карточках индикаторов и значениях показателей.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[MeasurementUnit] | Список единиц измерения индикаторов.
    
    Поля модели:
    MeasurementUnit:
    Поле | Тип | Описание
    measurement_unit_id | int | Идентификатор единицы измерения.
    name | str | Название единицы измерения.
    
    Пример вызова:
    {
      "tool": "GetMeasurementUnits",
      "arguments": {}
    }
    
    Пример результата:
    [
      {"measurement_unit_id": 1, "name": "человек"}
    ]
    """,
    tags=["indicators"],
    annotations={"title": "GetMeasurementUnits", "readOnlyHint": True},
)
async def get_measurement_units(request: Request = CurrentRequest()) -> list[MeasurementUnit]:
    """Get a list of measurement units."""
    indicators_service: IndicatorsService = request.state.indicators_service
    measurement_units = await indicators_service.get_measurement_units()
    return [MeasurementUnit.from_dto(measurement_unit) for measurement_unit in measurement_units]


@indicators_mcp.tool(
    name="GetIndicatorsGroups",
    title="Получить группы индикаторов",
    description="""Возвращает справочник групп индикаторов вместе с краткими карточками индикаторов, входящих в каждую группу.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[IndicatorsGroup] | Список групп индикаторов.
    
    Поля модели:
    IndicatorsGroup:
    Поле | Тип | Описание
    indicators_group_id | int | Идентификатор группы индикаторов.
    name | str | Название группы индикаторов.
    indicators | list | Краткие сведения об индикаторах, включенных в группу.
    
    Пример вызова:
    {
      "tool": "GetIndicatorsGroups",
      "arguments": {}
    }
    
    Пример результата:
    [
      {
        "indicators_group_id": 1,
        "name": "Демография",
        "indicators": [
          {"indicator_id": 10, "parent_id": null, "name_full": "Численность населения", "measurement_unit": {"id": 1, "name": "человек"}, "level": 1, "list_label": "1"}
        ]
      }
    ]
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorsGroups", "readOnlyHint": True},
)
async def get_indicators_groups(request: Request = CurrentRequest()) -> list[IndicatorsGroup]:
    """Get all indicators groups."""
    indicators_service: IndicatorsService = request.state.indicators_service
    groups = await indicators_service.get_indicators_groups()
    return [IndicatorsGroup.from_dto(group) for group in groups]


@indicators_mcp.tool(
    name="GetIndicatorsByGroupId",
    title="Получить индикаторы группы",
    description="""Возвращает полный список индикаторов, привязанных к выбранной группе индикаторов.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicators_group_id | int | да | Идентификатор группы, по которой нужно получить индикаторы.
    
    Выходные данные:
    list[Indicator] | Список индикаторов выбранной группы.
    
    Поля модели:
    Indicator:
    Поле | Тип | Описание
    indicator_id | int | Идентификатор индикатора.
    name_full | str | Полное название индикатора.
    name_short | str | Краткое название индикатора.
    measurement_unit | MeasurementUnitBasic | None | Единица измерения индикатора.
    service_type | ServiceTypeBasic | None | Тип сервиса, если индикатор связан с сервисами.
    physical_object_type | PhysicalObjectTypeBasic | None | Тип физического объекта, если индикатор связан с объектами.
    level | int | Уровень индикатора в иерархии.
    list_label | str | Маркер индикатора в иерархическом списке.
    parent_id | int | None | Идентификатор родительского индикатора.
    created_at | datetime | Дата и время создания индикатора.
    updated_at | datetime | Дата и время последнего обновления индикатора.
    
    Пример вызова:
    {
      "tool": "GetIndicatorsByGroupId",
      "arguments": {
        "indicators_group_id": 1
      }
    }
    
    Пример результата:
    [
      {
        "indicator_id": 10,
        "name_full": "Численность населения",
        "name_short": "Население",
        "measurement_unit": {"id": 1, "name": "человек"},
        "service_type": null,
        "physical_object_type": null,
        "level": 1,
        "list_label": "1",
        "parent_id": null,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32001 Not found: группа индикаторов не найдена.
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorsByGroupId", "readOnlyHint": True},
)
async def get_indicators_by_group_id(
    indicators_group_id: Annotated[int, "Идентификатор группы индикаторов"],
    request: Request = CurrentRequest(),
) -> list[Indicator]:
    """Get indicators by group identifier."""
    indicators_service: IndicatorsService = request.state.indicators_service
    indicators = await indicators_service.get_indicators_by_group_id(indicators_group_id)
    return [Indicator.from_dto(indicator) for indicator in indicators]


@indicators_mcp.tool(
    name="GetIndicatorsByParent",
    title="Получить индикаторы по родителю",
    description="""Возвращает индикаторы из иерархии по родительскому индикатору, имени родителя и дополнительным фильтрам.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительского индикатора; нельзя передавать одновременно с parent_name.
    parent_name | Optional[str] | нет | Полное название родительского индикатора; нельзя передавать одновременно с parent_id.
    name | Optional[str] | нет | Фильтр по подстроке в названии индикатора без учета регистра.
    territory_id | Optional[int] | нет | Фильтр по территории, для которой доступны индикаторы.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса, связанному с индикатором.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта, связанному с индикатором.
    get_all_subtree | bool | нет | Если true, возвращается все поддерево найденного родителя, а не только ближайшие дочерние индикаторы.
    
    Выходные данные:
    list[Indicator] | Список индикаторов, соответствующих фильтрам.
    
    Поля модели:
    Indicator:
    Поле | Тип | Описание
    indicator_id | int | Идентификатор индикатора.
    name_full | str | Полное название индикатора.
    name_short | str | Краткое название индикатора.
    measurement_unit | MeasurementUnitBasic | None | Единица измерения индикатора.
    service_type | ServiceTypeBasic | None | Тип сервиса, если индикатор связан с сервисами.
    physical_object_type | PhysicalObjectTypeBasic | None | Тип физического объекта, если индикатор связан с объектами.
    level | int | Уровень индикатора в иерархии.
    list_label | str | Маркер индикатора в иерархическом списке.
    parent_id | int | None | Идентификатор родительского индикатора.
    created_at | datetime | Дата и время создания индикатора.
    updated_at | datetime | Дата и время последнего обновления индикатора.
    
    Пример вызова:
    {
      "tool": "GetIndicatorsByParent",
      "arguments": {
        "parent_id": 1,
        "name": "население",
        "get_all_subtree": true
      }
    }
    
    Пример результата:
    [
      {
        "indicator_id": 10,
        "name_full": "Численность населения",
        "name_short": "Население",
        "measurement_unit": {"id": 1, "name": "человек"},
        "service_type": null,
        "physical_object_type": null,
        "level": 2,
        "list_label": "1.1",
        "parent_id": 1,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: одновременно переданы parent_id и parent_name.
    - -32001 Not found: родительский индикатор, территория, тип сервиса или тип физического объекта не найдены.
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorsByParent", "readOnlyHint": True},
)
async def get_indicators_by_parent(
    parent_id: Annotated[Optional[int], "Идентификатор родительского индикатора"] = None,
    parent_name: Annotated[Optional[str], "Полное имя родительского индикатора"] = None,
    name: Annotated[Optional[str], "Фильтр по имени индикатора"] = None,
    territory_id: Annotated[Optional[int], "Фильтр по территории"] = None,
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    get_all_subtree: Annotated[bool, "Получить всё поддерево индикаторов"] = False,
    request: Request = CurrentRequest(),
) -> list[Indicator]:
    """Get indicators by parent identifier or name."""
    indicators_service: IndicatorsService = request.state.indicators_service

    if parent_id is not None and parent_name is not None:
        raise McpError(
            ErrorData(code=-32602, message="Укажите только один способ поиска родителя: parent_id или parent_name.")
        )

    indicators = await indicators_service.get_indicators_by_parent(
        parent_id, parent_name, name, territory_id, service_type_id, physical_object_type_id, get_all_subtree
    )

    return [Indicator.from_dto(indicator) for indicator in indicators]


@indicators_mcp.tool(
    name="GetIndicatorById",
    title="Получить индикатор по идентификатору",
    description="""Возвращает полную карточку индикатора по его идентификатору.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicator_id | int | да | Идентификатор индикатора, который нужно получить.
    
    Выходные данные:
    Indicator | Полная карточка индикатора.
    
    Поля модели:
    Indicator:
    Поле | Тип | Описание
    indicator_id | int | Идентификатор индикатора.
    name_full | str | Полное название индикатора.
    name_short | str | Краткое название индикатора.
    measurement_unit | MeasurementUnitBasic | None | Единица измерения индикатора.
    service_type | ServiceTypeBasic | None | Тип сервиса, если индикатор связан с сервисами.
    physical_object_type | PhysicalObjectTypeBasic | None | Тип физического объекта, если индикатор связан с объектами.
    level | int | Уровень индикатора в иерархии.
    list_label | str | Маркер индикатора в иерархическом списке.
    parent_id | int | None | Идентификатор родительского индикатора.
    created_at | datetime | Дата и время создания индикатора.
    updated_at | datetime | Дата и время последнего обновления индикатора.
    
    Пример вызова:
    {
      "tool": "GetIndicatorById",
      "arguments": {
        "indicator_id": 1
      }
    }
    
    Пример результата:
    {
      "indicator_id": 10,
      "name_full": "Численность населения",
      "name_short": "Население",
      "measurement_unit": {"id": 1, "name": "человек"},
      "service_type": null,
      "physical_object_type": null,
      "level": 1,
      "list_label": "1",
      "parent_id": null,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
    
    Ошибки:
    - -32001 Not found: индикатор с указанным indicator_id не найден.
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorById", "readOnlyHint": True},
)
async def get_indicator_by_id(
    indicator_id: Annotated[int, "Идентификатор индикатора"],
    request: Request = CurrentRequest(),
) -> Indicator:
    """Get an indicator by identifier."""
    indicators_service: IndicatorsService = request.state.indicators_service
    indicator = await indicators_service.get_indicator_by_id(indicator_id)
    return Indicator.from_dto(indicator)


@indicators_mcp.tool(
    name="GetIndicatorValueById",
    title="Получить значение индикатора по идентификатору",
    description="""Возвращает одно сохраненное значение индикатора по идентификатору значения.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicator_value_id | int | да | Идентификатор записи значения индикатора.
    
    Выходные данные:
    IndicatorValue | Запись значения индикатора для территории и даты.
    
    Поля модели:
    IndicatorValue:
    Поле | Тип | Описание
    indicator_value_id | int | Идентификатор значения индикатора.
    indicator | ShortIndicatorInfo | Краткая карточка индикатора.
    territory | ShortTerritory | Территория, к которой относится значение.
    date_type | Literal | Тип временного периода: year, half_year, quarter, month или day.
    date_value | date | Дата начала периода значения.
    value | float | Числовое значение индикатора.
    value_type | Literal | Тип значения: real, forecast или target.
    information_source | str | Источник информации для значения.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetIndicatorValueById",
      "arguments": {
        "indicator_value_id": 1
      }
    }
    
    Пример результата:
    {
      "indicator_value_id": 100,
      "indicator": {"indicator_id": 10, "parent_id": null, "name_full": "Численность населения", "measurement_unit": {"id": 1, "name": "человек"}, "level": 1, "list_label": "1"},
      "territory": {"id": 1, "name": "Пермь"},
      "date_type": "year",
      "date_value": "2024-01-01",
      "value": 1034000.0,
      "value_type": "real",
      "information_source": "Росстат",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
    
    Ошибки:
    - -32001 Not found: значение индикатора с указанным indicator_value_id не найдено.
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorValueById", "readOnlyHint": True},
)
async def get_indicator_value_by_id(
    indicator_value_id: Annotated[int, "Идентификатор значения индикатора"],
    request: Request = CurrentRequest(),
) -> IndicatorValue:
    """Get an indicator value by identifier."""
    indicators_service: IndicatorsService = request.state.indicators_service
    indicator_value = await indicators_service.get_indicator_value_by_id(indicator_value_id)
    return IndicatorValue.from_dto(indicator_value)


@indicators_mcp.tool(
    name="GetIndicatorValuesByIndicatorId",
    title="Получить значения индикатора",
    description="""Возвращает значения выбранного индикатора с фильтрами по территории, периоду, типу значения и источнику.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicator_id | int | да | Идентификатор индикатора, значения которого нужно получить.
    territory_id | Optional[int] | нет | Фильтр по территории.
    date_type | Optional[DateType] | нет | Фильтр по типу периода: year, half_year, quarter, month или day.
    date_value | Optional[date] | нет | Фильтр по дате начала периода.
    value_type | Optional[ValueType] | нет | Фильтр по типу значения: real, forecast или target.
    information_source | Optional[str] | нет | Фильтр по источнику информации.
    
    Выходные данные:
    list[IndicatorValue] | Список значений индикатора, соответствующих фильтрам.
    
    Поля модели:
    IndicatorValue:
    Поле | Тип | Описание
    indicator_value_id | int | Идентификатор значения индикатора.
    indicator | ShortIndicatorInfo | Краткая карточка индикатора.
    territory | ShortTerritory | Территория, к которой относится значение.
    date_type | Literal | Тип временного периода: year, half_year, quarter, month или day.
    date_value | date | Дата начала периода значения.
    value | float | Числовое значение индикатора.
    value_type | Literal | Тип значения: real, forecast или target.
    information_source | str | Источник информации для значения.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetIndicatorValuesByIndicatorId",
      "arguments": {
        "indicator_id": 1,
        "territory_id": 1,
        "date_type": "year",
        "date_value": "2024-01-01",
        "value_type": "real",
        "information_source": "Росстат"
      }
    }
    
    Пример результата:
    [
      {
        "indicator_value_id": 100,
        "indicator": {"indicator_id": 10, "parent_id": null, "name_full": "Численность населения", "measurement_unit": {"id": 1, "name": "человек"}, "level": 1, "list_label": "1"},
        "territory": {"id": 1, "name": "Пермь"},
        "date_type": "year",
        "date_value": "2024-01-01",
        "value": 1034000.0,
        "value_type": "real",
        "information_source": "Росстат",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32001 Not found: индикатор, территория или значения по указанным фильтрам не найдены.
    """,
    tags=["indicators"],
    annotations={"title": "GetIndicatorValuesByIndicatorId", "readOnlyHint": True},
)
async def get_indicator_values_by_id(
    indicator_id: Annotated[int, "Идентификатор индикатора"],
    territory_id: Annotated[Optional[int], "Фильтр по территории"] = None,
    date_type: Annotated[Optional[DateType], "Фильтр по типу даты"] = None,
    date_value: Annotated[Optional[date], "Фильтр по значению даты"] = None,
    value_type: Annotated[Optional[ValueType], "Фильтр по типу значения"] = None,
    information_source: Annotated[Optional[str], "Фильтр по источнику информации"] = None,
    request: Request = CurrentRequest(),
) -> list[IndicatorValue]:
    """Get indicator values by indicator identifier."""
    indicators_service: IndicatorsService = request.state.indicators_service

    date_type_field = date_type.value if date_type is not None else None
    value_type_field = value_type.value if value_type is not None else None

    indicator_values = await indicators_service.get_indicator_values_by_id(
        indicator_id, territory_id, date_type_field, date_value, value_type_field, information_source
    )

    return [IndicatorValue.from_dto(value) for value in indicator_values]


@indicators_mcp.tool(
    name="GetIndicatorsByTerritoryId",
    title="Получить индикаторы территории",
    description="""Возвращает индикаторы, для которых на указанной территории есть значения или привязки.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, для которой нужно получить доступные индикаторы.
    
    Выходные данные:
    list[Indicator] | Список индикаторов территории.
    
    Поля модели:
    Indicator:
    Поле | Тип | Описание
    indicator_id | int | Идентификатор индикатора.
    name_full | str | Полное название индикатора.
    name_short | str | Краткое название индикатора.
    measurement_unit | MeasurementUnitBasic | None | Единица измерения индикатора.
    service_type | ServiceTypeBasic | None | Тип сервиса, если индикатор связан с сервисами.
    physical_object_type | PhysicalObjectTypeBasic | None | Тип физического объекта, если индикатор связан с объектами.
    level | int | Уровень индикатора в иерархии.
    list_label | str | Маркер индикатора в иерархическом списке.
    parent_id | int | None | Идентификатор родительского индикатора.
    created_at | datetime | Дата и время создания индикатора.
    updated_at | datetime | Дата и время последнего обновления индикатора.
    
    Пример вызова:
    {
      "tool": "GetIndicatorsByTerritoryId",
      "arguments": {
        "territory_id": 1
      }
    }
    
    Пример результата:
    [
      {
        "indicator_id": 10,
        "name_full": "Численность населения",
        "name_short": "Население",
        "measurement_unit": {"id": 1, "name": "человек"},
        "service_type": null,
        "physical_object_type": null,
        "level": 1,
        "list_label": "1",
        "parent_id": null,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32001 Not found: территория не найдена или для нее нет доступных индикаторов.
    """,
    tags=["indicators", "territories"],
    annotations={"title": "GetIndicatorsByTerritoryId", "readOnlyHint": True},
)
async def get_indicators_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    request: Request = CurrentRequest(),
) -> list[Indicator]:
    """Get indicators for a territory."""
    territories_service: TerritoriesService = request.state.territories_service
    indicators = await territories_service.get_indicators_by_territory_id(territory_id)
    return [Indicator.from_dto(indicator) for indicator in indicators]


@indicators_mcp.tool(
    name="GetTerritoryIndicatorValuesGeoJSON",
    title="Получить значения индикаторов территории в формате GeoJSON",
    description="""Возвращает значения индикаторов для указанной территории в формате GeoJSON с геометрией территории или ее центром.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, для которой нужно получить значения индикаторов.
    indicator_ids | Optional[str] | нет | Список идентификаторов индикаторов через запятую, например "1,2,3".
    indicators_group_id | Optional[int] | нет | Фильтр по группе индикаторов.
    start_date | Optional[date] | нет | Начальная дата периода отбора значений.
    end_date | Optional[date] | нет | Конечная дата периода отбора значений.
    value_type | Optional[ValueType] | нет | Фильтр по типу значения: real, forecast или target.
    information_source | Optional[str] | нет | Фильтр по источнику информации.
    last_only | bool | нет | Если true, возвращаются только последние значения по каждому индикатору.
    centers_only | bool | нет | Если true, вместо геометрии территории возвращается ее центр.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, TerritoryWithBinnedIndicators]] | GeoJSON FeatureCollection с одной территорией и списком значений индикаторов в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    TerritoryWithBinnedIndicators:
    Поле | Тип | Описание
    territory_id | int | Идентификатор территории.
    name | str | Название территории.
    is_city | bool | Признак города.
    centre_point | Point | Центр территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    indicators | list | Значения индикаторов с бинами binned_min_value и binned_max_value.
    
    Пример вызова:
    {
      "tool": "GetTerritoryIndicatorValuesGeoJSON",
      "arguments": {
        "territory_id": 1,
        "indicator_ids": "1,2",
        "indicators_group_id": 1,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "value_type": "real",
        "last_only": true,
        "centers_only": false
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
            "territory_id": 1,
            "name": "Пермь",
            "is_city": true,
            "centre_point": {"type": "Point", "coordinates": [56.25, 58.01]},
            "territory_type": {"id": 1, "name": "Город"},
            "indicators": [
              {"indicator_id": 10, "name_full": "Численность населения", "measurement_unit_name": "человек", "level": 1, "list_label": "1", "date_value": "2024-01-01", "value": 1034000.0, "value_type": "real", "information_source": "Росстат", "binned_min_value": 1000000.0, "binned_max_value": 1100000.0}
            ]
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: indicator_ids содержит нецелочисленное значение.
    - -32001 Not found: территория, группа индикаторов или один из индикаторов не найдены.
    """,
    tags=["indicators", "territories"],
    annotations={"title": "GetTerritoryIndicatorValuesGeoJSON", "readOnlyHint": True},
)
async def get_indicator_values_with_geometry_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    indicator_ids: Annotated[Optional[str], "Список идентификаторов индикаторов через запятую"] = None,
    indicators_group_id: Annotated[Optional[int], "Фильтр по группе индикаторов"] = None,
    start_date: Annotated[Optional[date], "Начальная дата периода"] = None,
    end_date: Annotated[Optional[date], "Конечная дата периода"] = None,
    value_type: Annotated[Optional[ValueType], "Фильтр по типу значения"] = None,
    information_source: Annotated[Optional[str], "Фильтр по источнику"] = None,
    last_only: Annotated[bool, "Возвращать только последние значения"] = True,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithBinnedIndicators]]:
    """Get indicator values for a territory in GeoJSON format."""
    territories_service: TerritoriesService = request.state.territories_service

    parsed_indicator_ids = _parse_indicator_ids(indicator_ids)
    value_type_field = value_type.value if value_type is not None else None

    territory = await territories_service.get_indicator_values_with_geometry_by_territory_id(
        territory_id,
        parsed_indicator_ids,
        indicators_group_id,
        start_date,
        end_date,
        value_type_field,
        information_source,
        last_only,
    )

    return await GeoJSONResponse.from_list([territory.to_geojson_dict()], centers_only, save_centers=True)


@indicators_mcp.tool(
    name="GetTerritoryIndicatorValues",
    title="Получить значения индикаторов территории",
    description="""Возвращает значения индикаторов для территории в виде списка, с возможностью включить дочерние территории и города.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории, для которой нужно получить значения индикаторов.
    indicator_ids | Optional[str] | нет | Список идентификаторов индикаторов через запятую, например "1,2,3".
    indicators_group_id | Optional[int] | нет | Фильтр по группе индикаторов.
    start_date | Optional[date] | нет | Начальная дата периода отбора значений.
    end_date | Optional[date] | нет | Конечная дата периода отбора значений.
    value_type | Optional[ValueType] | нет | Фильтр по типу значения: real, forecast или target.
    information_source | Optional[str] | нет | Фильтр по источнику информации.
    last_only | bool | нет | Если true, возвращаются только последние значения по каждому индикатору.
    include_child_territories | bool | нет | Если true, значения собираются также по дочерним территориям.
    cities_only | bool | нет | Если true, среди дочерних территорий учитываются только города; допустимо только при include_child_territories=true.
    
    Выходные данные:
    list[BinnedIndicatorValue] | Список значений индикаторов с расчетными границами бинов.
    
    Поля модели:
    BinnedIndicatorValue:
    Поле | Тип | Описание
    indicator_value_id | int | Идентификатор значения индикатора.
    indicator | ShortIndicatorInfo | Краткая карточка индикатора.
    territory | ShortTerritory | Территория, к которой относится значение.
    date_type | Literal | Тип временного периода: year, half_year, quarter, month или day.
    date_value | date | Дата начала периода значения.
    value | float | Числовое значение индикатора.
    value_type | Literal | Тип значения: real, forecast или target.
    information_source | str | Источник информации для значения.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    binned_min_value | float | None | Нижняя граница бина для значения.
    binned_max_value | float | None | Верхняя граница бина для значения.
    
    Пример вызова:
    {
      "tool": "GetTerritoryIndicatorValues",
      "arguments": {
        "territory_id": 1,
        "indicator_ids": "1,2",
        "indicators_group_id": 1,
        "include_child_territories": true,
        "cities_only": false
      }
    }
    
    Пример результата:
    [
      {
        "indicator_value_id": 100,
        "indicator": {"indicator_id": 10, "parent_id": null, "name_full": "Численность населения", "measurement_unit": {"id": 1, "name": "человек"}, "level": 1, "list_label": "1"},
        "territory": {"id": 1, "name": "Пермь"},
        "date_type": "year",
        "date_value": "2024-01-01",
        "value": 1034000.0,
        "value_type": "real",
        "information_source": "Росстат",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
        "binned_min_value": 1000000.0,
        "binned_max_value": 1100000.0
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: indicator_ids содержит нецелочисленное значение.
    - -32602 Invalid params: cities_only=true передан при include_child_territories=false.
    - -32001 Not found: территория, группа индикаторов или один из индикаторов не найдены.
    """,
    tags=["indicators", "territories"],
    annotations={"title": "GetTerritoryIndicatorValues", "readOnlyHint": True},
)
async def get_indicator_values_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    indicator_ids: Annotated[Optional[str], "Список идентификаторов индикаторов через запятую"] = None,
    indicators_group_id: Annotated[Optional[int], "Фильтр по группе индикаторов"] = None,
    start_date: Annotated[Optional[date], "Начальная дата периода"] = None,
    end_date: Annotated[Optional[date], "Конечная дата периода"] = None,
    value_type: Annotated[Optional[ValueType], "Фильтр по типу значения"] = None,
    information_source: Annotated[Optional[str], "Фильтр по источнику"] = None,
    last_only: Annotated[bool, "Возвращать только последние значения"] = True,
    include_child_territories: Annotated[bool, "Включать дочерние территории"] = False,
    cities_only: Annotated[bool, "Возвращать только города"] = False,
    request: Request = CurrentRequest(),
) -> list[BinnedIndicatorValue]:
    """Get indicator values for a territory."""
    territories_service: TerritoriesService = request.state.territories_service

    if not include_child_territories and cities_only:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр cities_only можно использовать только при include_child_territories=true.",
            )
        )

    parsed_indicator_ids = _parse_indicator_ids(indicator_ids)
    value_type_field = value_type.value if value_type is not None else None

    indicator_values = await territories_service.get_indicator_values_by_territory_id(
        territory_id,
        parsed_indicator_ids,
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


@indicators_mcp.tool(
    name="GetIndicatorValuesByParentTerritory",
    title="Получить значения индикаторов дочерних территорий",
    description="""Возвращает значения индикаторов для дочерних территорий выбранной территории в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    parent_id | Optional[int] | нет | Идентификатор родительской территории; если не указан, используются территории верхнего уровня.
    indicator_ids | Optional[str] | нет | Список идентификаторов индикаторов через запятую, например "1,2,3".
    indicators_group_id | Optional[int] | нет | Фильтр по группе индикаторов.
    start_date | Optional[date] | нет | Начальная дата периода отбора значений.
    end_date | Optional[date] | нет | Конечная дата периода отбора значений.
    value_type | Optional[ValueType] | нет | Фильтр по типу значения: real, forecast или target.
    information_source | Optional[str] | нет | Фильтр по источнику информации.
    last_only | bool | нет | Если true, возвращаются только последние значения по каждому индикатору.
    with_binned | bool | нет | Если true, дополнительно возвращаются агрегированные бины по территориям.
    centers_only | bool | нет | Если true, вместо геометрии территорий возвращаются их центры.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]] | TerritoriesWithBinnedIndicators | GeoJSON дочерних территорий с индикаторами; при with_binned=true дополнительно возвращается список бинов.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    TerritoryWithIndicators:
    Поле | Тип | Описание
    territory_id | int | Идентификатор дочерней территории.
    name | str | Название дочерней территории.
    is_city | bool | Признак города.
    centre_point | Point | Центр территории.
    territory_type | TerritoryTypeBasic | Тип территории.
    indicators | list | Значения индикаторов на территории.
    TerritoriesWithBinnedIndicators:
    Поле | Тип | Описание
    geojson | GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]] | GeoJSON с дочерними территориями и их значениями индикаторов.
    binned | list | Агрегированные бины значений индикаторов по территориям.
    
    Пример вызова:
    {
      "tool": "GetIndicatorValuesByParentTerritory",
      "arguments": {
        "parent_id": 1,
        "indicator_ids": "1,2",
        "indicators_group_id": 1,
        "with_binned": true,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "geojson": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.3, 58.0], [56.3, 58.1], [56.2, 58.0]]]},
            "properties": {
              "territory_id": 2,
              "name": "Дочерняя территория",
              "is_city": true,
              "centre_point": {"type": "Point", "coordinates": [56.25, 58.01]},
              "territory_type": {"id": 1, "name": "Город"},
              "indicators": [
                {"indicator_id": 10, "name_full": "Численность населения", "measurement_unit_name": "человек", "level": 1, "list_label": "1", "date_value": "2024-01-01", "value": 120000.0, "value_type": "real", "information_source": "Росстат"}
              ]
            }
          }
        ]
      },
      "binned": [
        {"territory": {"id": 2, "name": "Дочерняя территория"}, "indicator": {"indicator_id": 10, "name_full": "Численность населения"}, "min_value": 100000.0, "max_value": 150000.0}
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: indicator_ids содержит нецелочисленное значение.
    - -32001 Not found: родительская территория, группа индикаторов или один из индикаторов не найдены.
    """,
    tags=["indicators", "territories"],
    annotations={"title": "GetIndicatorValuesByParentTerritory", "readOnlyHint": True},
)
async def get_indicator_values_by_parent_id(
    parent_id: Annotated[Optional[int], "Идентификатор родительской территории"] = None,
    indicator_ids: Annotated[Optional[str], "Список идентификаторов индикаторов через запятую"] = None,
    indicators_group_id: Annotated[Optional[int], "Фильтр по группе индикаторов"] = None,
    start_date: Annotated[Optional[date], "Начальная дата периода"] = None,
    end_date: Annotated[Optional[date], "Конечная дата периода"] = None,
    value_type: Annotated[Optional[ValueType], "Фильтр по типу значения"] = None,
    information_source: Annotated[Optional[str], "Фильтр по источнику"] = None,
    last_only: Annotated[bool, "Возвращать только последние значения"] = True,
    with_binned: Annotated[bool, "Вернуть агрегированные бинды"] = False,
    centers_only: Annotated[bool, "Возвращать только центры геометрий"] = False,
    request: Request = CurrentRequest(),
) -> GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]] | TerritoriesWithBinnedIndicators:
    """Get indicator values for child territories in GeoJSON format."""
    territories_service: TerritoriesService = request.state.territories_service

    parsed_indicator_ids = _parse_indicator_ids(indicator_ids)
    value_type_field = value_type.value if value_type is not None else None

    territories, binned = await territories_service.get_indicator_values_by_parent_id(
        parent_id,
        parsed_indicator_ids,
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
            binned=[ShortTerritoryIndicatorBind.from_dto(bind) for bind in binned],
        )

    return await GeoJSONResponse.from_list(
        [territory.to_geojson_dict() for territory in territories], centers_only, save_centers=True
    )


@indicators_mcp.tool(
    name="GetScenarioIndicatorsValues",
    title="Получить значения индикаторов сценария",
    description="""Возвращает значения индикаторов, сохраненные для текущего сценария, с фильтрами по индикаторам, территории и гексагону.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicator_ids | Optional[str] | нет | Список идентификаторов индикаторов через запятую, например "1,2,3".
    indicators_group_id | Optional[int] | нет | Фильтр по группе индикаторов.
    territory_id | Optional[int] | нет | Фильтр по территории сценария.
    hexagon_id | Optional[int] | нет | Фильтр по гексагону сценария.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    list[ScenarioIndicatorValue] | Список значений индикаторов текущего сценария.
    
    Поля модели:
    ScenarioIndicatorValue:
    Поле | Тип | Описание
    indicator_value_id | int | Идентификатор значения индикатора сценария.
    indicator | ShortIndicatorInfo | Краткая карточка индикатора.
    scenario | ShortScenario | Сценарий, к которому относится значение.
    territory | ShortTerritory | None | Территория сценария, если значение задано для территории.
    hexagon_id | int | None | Идентификатор гексагона, если значение задано для гексагона.
    value | float | Числовое значение индикатора.
    comment | str | None | Комментарий к сценарию значения.
    information_source | str | None | Источник информации или способ расчета.
    properties | dict | Дополнительные свойства значения.
    created_at | datetime | Дата и время создания записи.
    updated_at | datetime | Дата и время последнего обновления записи.
    
    Пример вызова:
    {
      "tool": "GetScenarioIndicatorsValues",
      "arguments": {
        "indicator_ids": "1,2",
        "indicators_group_id": 1,
        "territory_id": 1
      }
    }
    
    Пример результата:
    [
      {
        "indicator_value_id": 200,
        "indicator": {"indicator_id": 10, "parent_id": null, "name_full": "Численность населения", "measurement_unit": {"id": 1, "name": "человек"}, "level": 1, "list_label": "1"},
        "scenario": {"id": 5, "name": "Базовый сценарий"},
        "territory": {"id": 1, "name": "Пермь"},
        "hexagon_id": null,
        "value": 1040000.0,
        "comment": "Модельный расчет",
        "information_source": "modeled",
        "properties": {},
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: indicator_ids содержит нецелочисленное значение.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, территория, гексагон, группа индикаторов или один из индикаторов не найдены.
    """,
    tags=["indicators", "scenarios"],
    annotations={"title": "GetScenarioIndicatorsValues", "readOnlyHint": True},
)
async def get_indicators_values_by_scenario_id(
    indicator_ids: Annotated[Optional[str], "Список идентификаторов индикаторов через запятую"] = None,
    indicators_group_id: Annotated[Optional[int], "Фильтр по группе индикаторов"] = None,
    territory_id: Annotated[Optional[int], "Фильтр по территории"] = None,
    hexagon_id: Annotated[Optional[int], "Фильтр по гексагону"] = None,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> list[ScenarioIndicatorValue]:
    """Get indicator values for the current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    parsed_indicator_ids = _parse_indicator_ids(indicator_ids)

    indicators = await user_project_service.get_scenario_indicators_values(
        scenario_id, parsed_indicator_ids, indicators_group_id, territory_id, hexagon_id, user
    )

    return [ScenarioIndicatorValue.from_dto(indicator) for indicator in indicators]


@indicators_mcp.tool(
    name="GetScenarioHexagonsWithIndicatorsValues",
    title="Получить гексагоны сценария со значениями индикаторов",
    description="""Возвращает гексагоны текущего сценария со значениями выбранных индикаторов в формате GeoJSON.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    indicator_ids | Optional[str] | нет | Список идентификаторов индикаторов через запятую, например "1,2,3".
    indicators_group_id | Optional[int] | нет | Фильтр по группе индикаторов.
    centers_only | bool | нет | Если true, вместо геометрии гексагонов возвращаются их центры.
    metadata.scenario_id | int | да | Идентификатор сценария в metadata MCP-запроса.
    
    Выходные данные:
    GeoJSONResponse[Feature[Geometry, HexagonWithIndicators]] | GeoJSON FeatureCollection с гексагонами и значениями индикаторов в properties.
    
    Поля модели:
    GeoJSONResponse:
    Поле | Тип | Описание
    type | str | Тип GeoJSON-коллекции.
    features | list | Список объектов Feature; каждый содержит geometry и properties.
    HexagonWithIndicators:
    Поле | Тип | Описание
    hexagon_id | int | Идентификатор гексагона.
    indicators | list | Значения проектных индикаторов на гексагоне.
    
    Пример вызова:
    {
      "tool": "GetScenarioHexagonsWithIndicatorsValues",
      "arguments": {
        "indicator_ids": "1,2",
        "indicators_group_id": 1,
        "centers_only": false
      }
    }
    
    Пример результата:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Polygon", "coordinates": [[[56.2, 58.0], [56.21, 58.0], [56.22, 58.01], [56.21, 58.02], [56.2, 58.02], [56.19, 58.01], [56.2, 58.0]]]},
          "properties": {
            "hexagon_id": 50,
            "indicators": [
              {"indicator_id": 10, "name_full": "Численность населения", "measurement_unit_name": "человек", "value": 1200.0, "comment": "Модельный расчет"}
            ]
          }
        }
      ]
    }
    
    Ошибки:
    - -32602 Invalid params: metadata.scenario_id отсутствует или не является целым числом.
    - -32602 Invalid params: indicator_ids содержит нецелочисленное значение.
    - -32000 Permission denied: у пользователя нет доступа к сценарию или проекту, которому он принадлежит.
    - -32001 Not found: сценарий, группа индикаторов или один из индикаторов не найдены.
    """,
    tags=["indicators", "scenarios"],
    annotations={"title": "GetScenarioHexagonsWithIndicatorsValues", "readOnlyHint": True},
)
async def get_hexagons_with_indicators_values_by_scenario_id(
    indicator_ids: Annotated[Optional[str], "Список идентификаторов индикаторов через запятую"] = None,
    indicators_group_id: Annotated[Optional[int], "Фильтр по группе индикаторов"] = None,
    centers_only: Annotated[bool, "Возвращать только центры гексагонов"] = False,
    request: Request = CurrentRequest(),
    context: Context = CurrentContext(),
    user: UserDTO | None = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, HexagonWithIndicators]]:
    """Get hexagons with indicator values for the current scenario."""
    user_project_service: UserProjectService = request.state.user_project_service
    scenario_id = _get_scenario_id(context)
    parsed_indicator_ids = _parse_indicator_ids(indicator_ids)

    hexagons = await user_project_service.get_hexagons_with_indicators_by_scenario_id(
        scenario_id, parsed_indicator_ids, indicators_group_id, user
    )

    return await GeoJSONResponse.from_list([hexagon.to_geojson_dict() for hexagon in hexagons], centers_only)
