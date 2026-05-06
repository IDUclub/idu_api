"""MCP tools for social groups and values are defined here."""

from typing import Annotated, Optional

from fastmcp.dependencies import CurrentRequest
from mcp import ErrorData, McpError
from starlette.requests import Request

from idu_api.urban_api.logic.soc_groups import SocGroupsService
from idu_api.urban_api.schemas import ServiceType, SocGroup, SocGroupWithServiceTypes, SocValue, SocValueIndicatorValue
from idu_api.urban_api.schemas.enums import Ordering

from .routers import soc_groups_mcp


@soc_groups_mcp.tool(
    name="GetSocialGroups",
    title="Получить социальные группы",
    description="""Возвращает справочник социальных групп населения, используемых при расчете потребности в городских сервисах и показателей обеспеченности.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[SocGroup] | Список социальных групп из справочника.
    
    Поля модели:
    SocGroup:
    Поле | Тип | Описание
    soc_group_id | int | Уникальный идентификатор социальной группы.
    name | str | Название социальной группы населения.
    
    Пример вызова:
    {
      "tool": "GetSocialGroups",
      "arguments": {}
    }
    
    Пример результата:
    [
      {"soc_group_id": 1, "name": "Дети школьного возраста"},
      {"soc_group_id": 2, "name": "Дети дошкольного возраста"}
    ]
    
    Ошибки:
    - -32001 Not found: справочник социальных групп недоступен или не найден.
    """,
    tags=["soc_groups"],
    annotations={"title": "GetSocialGroups", "readOnlyHint": True},
)
async def get_social_groups(request: Request = CurrentRequest()) -> list[SocGroup]:
    """Get all social groups."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service
    soc_groups = await soc_groups_service.get_social_groups()
    return [SocGroup.from_dto(group) for group in soc_groups]


@soc_groups_mcp.tool(
    name="GetSocialGroupById",
    title="Получить социальную группу по идентификатору",
    description="""Возвращает одну социальную группу по идентификатору вместе с типами сервисов, которые относятся к этой группе населения.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    soc_group_id | int | да | Идентификатор социальной группы из справочника.
    
    Выходные данные:
    SocGroupWithServiceTypes | Карточка социальной группы со списком связанных типов сервисов.
    
    Поля модели:
    SocGroupWithServiceTypes:
    Поле | Тип | Описание
    soc_group_id | int | Уникальный идентификатор социальной группы.
    name | str | Название социальной группы населения.
    service_types | list[SocServiceType] | Типы сервисов, которые учитываются для социальной группы.
    
    SocServiceType:
    Поле | Тип | Описание
    id | int | Идентификатор типа сервиса.
    name | str | Название типа сервиса.
    infrastructure_type | str | Тип инфраструктуры, к которому относится сервис.
    
    Пример вызова:
    {
      "tool": "GetSocialGroupById",
      "arguments": {
        "soc_group_id": 1
      }
    }
    
    Пример результата:
    {
      "soc_group_id": 1,
      "name": "Дети школьного возраста",
      "service_types": [
        {"id": 7, "name": "Школьное образование", "infrastructure_type": "basic"}
      ]
    }
    
    Ошибки:
    - -32001 Not found: социальная группа с указанным soc_group_id не найдена.
    """,
    tags=["soc_groups"],
    annotations={"title": "GetSocialGroupById", "readOnlyHint": True},
)
async def get_social_group_by_id(
    soc_group_id: Annotated[int, "Идентификатор социальной группы"],
    request: Request = CurrentRequest(),
) -> SocGroupWithServiceTypes:
    """Get social group by identifier."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service
    soc_group = await soc_groups_service.get_social_group_by_id(soc_group_id)
    return SocGroupWithServiceTypes.from_dto(soc_group)


@soc_groups_mcp.tool(
    name="GetSocialValues",
    title="Получить социальные ценности",
    description="""Возвращает справочник социальных ценностей с рангами, нормативными и декретными значениями для оценки качества обеспеченности сервисами.
    Входные параметры:
    отсутствуют
    
    Выходные данные:
    list[SocValue] | Список социальных ценностей из справочника.
    
    Поля модели:
    SocValue:
    Поле | Тип | Описание
    soc_value_id | int | Уникальный идентификатор социальной ценности.
    name | str | Название социальной ценности.
    rank | int | Ранг социальной ценности в системе оценки.
    normative_value | float | Нормативное значение социальной ценности.
    decree_value | float | Значение социальной ценности, закрепленное нормативным актом.
    
    Пример вызова:
    {
      "tool": "GetSocialValues",
      "arguments": {}
    }
    
    Пример результата:
    [
      {
        "soc_value_id": 3,
        "name": "Доступность образования",
        "rank": 1,
        "normative_value": 0.75,
        "decree_value": 0.8
      }
    ]
    
    Ошибки:
    - -32001 Not found: справочник социальных ценностей недоступен или не найден.
    """,
    tags=["soc_groups"],
    annotations={"title": "GetSocialValues", "readOnlyHint": True},
)
async def get_social_values(request: Request = CurrentRequest()) -> list[SocValue]:
    """Get all social values."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service
    soc_values = await soc_groups_service.get_social_values()
    return [SocValue.from_dto(value) for value in soc_values]


@soc_groups_mcp.tool(
    name="GetSocialValueById",
    title="Получить социальную ценность по идентификатору",
    description="""Возвращает социальную ценность по идентификатору с ее рангом и нормативными значениями для расчетов обеспеченности.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    soc_value_id | int | да | Идентификатор социальной ценности из справочника.
    
    Выходные данные:
    SocValue | Карточка социальной ценности.
    
    Поля модели:
    SocValue:
    Поле | Тип | Описание
    soc_value_id | int | Уникальный идентификатор социальной ценности.
    name | str | Название социальной ценности.
    rank | int | Ранг социальной ценности в системе оценки.
    normative_value | float | Нормативное значение социальной ценности.
    decree_value | float | Значение социальной ценности, закрепленное нормативным актом.
    
    Пример вызова:
    {
      "tool": "GetSocialValueById",
      "arguments": {
        "soc_value_id": 3
      }
    }
    
    Пример результата:
    {
      "soc_value_id": 3,
      "name": "Доступность образования",
      "rank": 1,
      "normative_value": 0.75,
      "decree_value": 0.8
    }
    
    Ошибки:
    - -32001 Not found: социальная ценность с указанным soc_value_id не найдена.
    """,
    tags=["soc_groups"],
    annotations={"title": "GetSocialValueById", "readOnlyHint": True},
)
async def get_social_value_by_id(
    soc_value_id: Annotated[int, "Идентификатор социальной ценности"],
    request: Request = CurrentRequest(),
) -> SocValue:
    """Get social value by identifier."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service
    soc_value = await soc_groups_service.get_social_value_by_id(soc_value_id)
    return SocValue.from_dto(soc_value)


@soc_groups_mcp.tool(
    name="GetServiceTypesBySocialValueId",
    title="Получить типы сервисов по социальной ценности",
    description="""Возвращает типы сервисов, связанные с указанной социальной ценностью, с учетом выбранного направления сортировки.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    soc_value_id | int | да | Идентификатор социальной ценности, для которой нужно получить типы сервисов.
    ordering | Ordering | нет | Направление сортировки списка типов сервисов: asc или desc.
    
    Выходные данные:
    list[ServiceType] | Список типов сервисов, связанных с социальной ценностью.
    
    Поля модели:
    ServiceType:
    Поле | Тип | Описание
    service_type_id | int | Уникальный идентификатор типа сервиса.
    urban_function | UrbanFunctionBasic | Городская функция, к которой относится тип сервиса.
    name | str | Название типа сервиса.
    capacity_modeled | int | None | Модельная мощность типа сервиса по умолчанию.
    code | str | Машиночитаемый код типа сервиса.
    infrastructure_type | Optional | Тип инфраструктуры сервиса.
    properties | dict | Дополнительные свойства типа сервиса.
    
    Пример вызова:
    {
      "tool": "GetServiceTypesBySocialValueId",
      "arguments": {
        "soc_value_id": 3,
        "ordering": "asc"
      }
    }
    
    Пример результата:
    [
      {
        "service_type_id": 7,
        "urban_function": {"id": 2, "name": "Образование"},
        "name": "Школьное образование",
        "capacity_modeled": 500,
        "code": "school",
        "infrastructure_type": "basic",
        "properties": {}
      }
    ]
    
    Ошибки:
    - -32001 Not found: социальная ценность с указанным soc_value_id не найдена или для нее нет связанных типов сервисов.
    """,
    tags=["soc_groups", "services"],
    annotations={"title": "GetServiceTypesBySocialValueId", "readOnlyHint": True},
)
async def get_service_types_by_soc_value_id(
    soc_value_id: Annotated[int, "Идентификатор социальной ценности"],
    ordering: Annotated[Ordering, "Направление сортировки списка типов сервисов"] = Ordering.ASC,
    request: Request = CurrentRequest(),
) -> list[ServiceType]:
    """Get service types by social value identifier."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service
    result = await soc_groups_service.get_service_types_by_social_value_id(soc_value_id, ordering.value)
    return [ServiceType.from_dto(service_type_dto) for service_type_dto in result]


@soc_groups_mcp.tool(
    name="GetSocialValueIndicatorValues",
    title="Получить значения индикатора социальной ценности",
    description="""Возвращает значения индикатора для указанной социальной ценности с фильтрацией по территории, году или режиму последних доступных значений.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    soc_value_id | int | да | Идентификатор социальной ценности, для которой нужно получить значения индикатора.
    territory_id | Optional[int] | нет | Идентификатор территории для ограничения выборки; если не передан, возвращаются значения по всем доступным территориям.
    year | Optional[int] | нет | Год моделирования значения; нельзя передавать одновременно с last_only=true.
    last_only | bool | нет | Если true, возвращаются только последние доступные значения по каждой территории; нельзя использовать вместе с year.
    
    Выходные данные:
    list[SocValueIndicatorValue] | Список значений индикатора социальной ценности по территориям и годам.
    
    Поля модели:
    SocValueIndicatorValue:
    Поле | Тип | Описание
    soc_value | SocValueBasic | Краткая карточка социальной ценности.
    territory | ShortTerritory | Территория, к которой относится значение индикатора.
    year | int | Год моделирования значения.
    value | float | Значение индикатора социальной ценности для территории и года.
    created_at | datetime | Дата и время создания значения.
    updated_at | datetime | Дата и время последнего обновления значения.
    
    SocValueBasic:
    Поле | Тип | Описание
    id | int | Идентификатор социальной ценности.
    name | str | Название социальной ценности.
    
    ShortTerritory:
    Поле | Тип | Описание
    id | int | Идентификатор территории.
    name | str | Название территории.
    
    Пример вызова:
    {
      "tool": "GetSocialValueIndicatorValues",
      "arguments": {
        "soc_value_id": 3,
        "territory_id": 10,
        "year": 2024
      }
    }
    
    Пример результата:
    [
      {
        "soc_value": {"id": 3, "name": "Доступность образования"},
        "territory": {"id": 10, "name": "Пермь"},
        "year": 2024,
        "value": 0.82,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ]
    
    Ошибки:
    - -32602 Invalid params: параметр year передан одновременно с last_only=true.
    - -32001 Not found: социальная ценность, территория или значения индикатора по указанным фильтрам не найдены.
    """,
    tags=["soc_groups", "indicators"],
    annotations={"title": "GetSocialValueIndicatorValues", "readOnlyHint": True},
)
async def get_social_value_indicator_values(
    soc_value_id: Annotated[int, "Идентификатор социальной ценности"],
    territory_id: Annotated[Optional[int], "Идентификатор территории для фильтрации значений"] = None,
    year: Annotated[Optional[int], "Год моделирования значения"] = None,
    last_only: Annotated[bool, "Возвращать только последние доступные значения"] = False,
    request: Request = CurrentRequest(),
) -> list[SocValueIndicatorValue]:
    """Get social value indicator values."""
    soc_groups_service: SocGroupsService = request.state.soc_groups_service

    if last_only and year is not None:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр year нельзя передавать одновременно с last_only=true.",
            )
        )

    soc_group_indicators = await soc_groups_service.get_social_value_indicator_values(
        soc_value_id, territory_id, year, last_only
    )
    return [SocValueIndicatorValue.from_dto(value) for value in soc_group_indicators]
