"""MCP tools for urban objects are defined here."""

from typing import Annotated, Optional

from fastmcp.dependencies import CurrentRequest
from starlette.requests import Request

from idu_api.urban_api.logic.urban_objects import UrbanObjectsService
from idu_api.urban_api.schemas import UrbanObject

from .routers import urban_objects_mcp


@urban_objects_mcp.tool(
    name="GetUrbanObjectById",
    title="Получить городские объект по идентификатору",
    description="""Возвращает городской объект по его идентификатору вместе с физическим объектом, геометрией и связанным сервисом.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    urban_object_id | int | да | Идентификатор городского объекта.

    Выходные данные:
    UrbanObject | Городской объект с полной связанной информацией.

    Поля модели:
    UrbanObject:
    Поле | Тип | Описание
    urban_object_id | int | Идентификатор городского объекта.
    physical_object | PhysicalObject | Физический объект, связанный с городским объектом.
    object_geometry | ObjectGeometry | Геометрия городского объекта.
    service | Service | None | Связанный сервис, если он существует.

    Пример вызова:
    {
      "tool": "GetUrbanObjectById",
      "arguments": {
        "urban_object_id": 1
      }
    }

    Пример результата:
    {
      "urban_object_id": 1,
      "physical_object": {
        "physical_object_id": 10,
        "name": "Школа №1"
      },
      "service": {
        "service_id": 5,
        "name": "Образование"
      }
    }

    Ошибки:
    - -32001 Not found: urban_object_id не найден.
    """,
    tags=["urban_objects"],
    annotations={"title": "GetUrbanObjectById", "readOnlyHint": True},
)
async def get_urban_object_by_id(
    urban_object_id: Annotated[int, "Идентификатор городского объекта"],
    request: Request = CurrentRequest(),
) -> UrbanObject:
    """Get an urban object by its identifier."""
    urban_objects_service: UrbanObjectsService = request.state.urban_objects_service
    urban_object = await urban_objects_service.get_urban_object_by_id(urban_object_id)
    return UrbanObject.from_dto(urban_object)


@urban_objects_mcp.tool(
    name="GetUrbanObjectsByPhysicalObjectId",
    title="Получить городские объекты по физические объект идентификатору",
    description="""Возвращает список городских объектов, связанных с указанным физическим объектом.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    physical_object_id | int | да | Идентификатор физического объекта.

    Выходные данные:
    list[UrbanObject] | Список городских объектов, связанных с физическим объектом.

    Поля модели:
    UrbanObject:
    Поле | Тип | Описание
    urban_object_id | int | Идентификатор городского объекта.
    physical_object | PhysicalObject | Физический объект, связанный с городским объектом.
    object_geometry | ObjectGeometry | Геометрия городского объекта.
    service | Service | None | Связанный сервис, если он существует.

    Пример вызова:
    {
      "tool": "GetUrbanObjectsByPhysicalObjectId",
      "arguments": {
        "physical_object_id": 10
      }
    }

    Пример результата:
    [
      {
        "urban_object_id": 1,
        "physical_object": {
          "physical_object_id": 10,
          "name": "Школа №1"
        },
        "object_geometry": {...},
        "service": {...},
      }
    ]

    Ошибки:
    - -32001 Not found: physical_object_id не найден.
    """,
    tags=["urban_objects", "physical_objects"],
    annotations={"title": "GetUrbanObjectsByPhysicalObjectId", "readOnlyHint": True},
)
async def get_urban_objects_by_physical_object_id(
    physical_object_id: Annotated[int, "Идентификатор физического объекта"],
    request: Request = CurrentRequest(),
) -> list[UrbanObject]:
    """Get urban objects by physical object identifier."""
    urban_objects_service: UrbanObjectsService = request.state.urban_objects_service
    urban_objects = await urban_objects_service.get_urban_object_by_physical_object_id(physical_object_id)
    return [UrbanObject.from_dto(urban_object) for urban_object in urban_objects]


@urban_objects_mcp.tool(
    name="GetUrbanObjectsByObjectGeometryId",
    title="Получить городские объекты по объект геометрия идентификатору",
    description="""Возвращает список городских объектов, использующих указанную геометрию объекта.

    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    object_geometry_id | int | да | Идентификатор геометрии объекта.

    Выходные данные:
    list[UrbanObject] | Список городских объектов, связанных с указанной геометрией.

    Поля модели:
    UrbanObject:
    Поле | Тип | Описание
    urban_object_id | int | Идентификатор городского объекта.
    physical_object | PhysicalObject | Физический объект, связанный с городским объектом.
    object_geometry | ObjectGeometry | Геометрия городского объекта.
    service | Service | None | Связанный сервис, если он существует.

    Пример вызова:
    {
      "tool": "GetUrbanObjectsByObjectGeometryId",
      "arguments": {
        "object_geometry_id": 100
      }
    }

    Пример результата:
    [
      {
        "urban_object_id": 1,
        "object_geometry": {
          "object_geometry_id": 100
        }
      }
    ]

    Ошибки:
    - -32001 Not found: object_geometry_id не найден.
    """,
    tags=["urban_objects", "object_geometries"],
    annotations={"title": "GetUrbanObjectsByObjectGeometryId", "readOnlyHint": True},
)
async def get_urban_objects_by_object_geometry_id(
    object_geometry_id: Annotated[int, "Идентификатор геометрии объекта"],
    request: Request = CurrentRequest(),
) -> list[UrbanObject]:
    """Get urban objects by object geometry identifier."""
    urban_objects_service: UrbanObjectsService = request.state.urban_objects_service
    urban_objects = await urban_objects_service.get_urban_object_by_object_geometry_id(object_geometry_id)
    return [UrbanObject.from_dto(urban_object) for urban_object in urban_objects]


@urban_objects_mcp.tool(
    name="GetUrbanObjectsByServiceId",
    title="Получить городские объекты по сервис идентификатору",
    description="""Возвращает список городских объектов, связанных с указанным сервисом.

    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    service_id | int | да | Идентификатор сервиса.

    Выходные данные:
    list[UrbanObject] | Список городских объектов, связанных с сервисом.

    Поля модели:
    UrbanObject:
    Поле | Тип | Описание
    urban_object_id | int | Идентификатор городского объекта.
    physical_object | PhysicalObject | Физический объект, связанный с городским объектом.
    object_geometry | ObjectGeometry | Геометрия городского объекта.
    service | Service | None | Связанный сервис.

    Пример вызова:
    {
      "tool": "GetUrbanObjectsByServiceId",
      "arguments": {
        "service_id": 5
      }
    }

    Пример результата:
    [
      {
        "urban_object_id": 1,
        "service": {
          "service_id": 5,
          "name": "Образование"
        }
      }
    ]

    Ошибки:
    - -32001 Not found: service_id не найден.
    """,
    tags=["urban_objects", "services"],
    annotations={"title": "GetUrbanObjectsByServiceId", "readOnlyHint": True},
)
async def get_urban_objects_by_service_id(
    service_id: Annotated[int, "Идентификатор сервиса"],
    request: Request = CurrentRequest(),
) -> list[UrbanObject]:
    """Get urban objects by service identifier."""
    urban_objects_service: UrbanObjectsService = request.state.urban_objects_service
    urban_objects = await urban_objects_service.get_urban_object_by_service_id(service_id)
    return [UrbanObject.from_dto(urban_object) for urban_object in urban_objects]


@urban_objects_mcp.tool(
    name="GetUrbanObjectsByTerritoryId",
    title="Получить городские объекты по территория идентификатору",
    description="""Возвращает список городских объектов, расположенных на указанной территории, с возможностью фильтрации по типу сервиса и типу физического объекта.
    Входные параметры:
    Параметр | Тип | Обязателен | Описание
    territory_id | int | да | Идентификатор территории.
    service_type_id | Optional[int] | нет | Фильтр по типу сервиса.
    physical_object_type_id | Optional[int] | нет | Фильтр по типу физического объекта.

    Выходные данные:
    list[UrbanObject] | Список городских объектов, соответствующих заданным фильтрам.

    Поля модели:
    UrbanObject:
    Поле | Тип | Описание
    urban_object_id | int | Идентификатор городского объекта.
    physical_object | PhysicalObject | Физический объект, связанный с городским объектом.
    object_geometry | ObjectGeometry | Геометрия городского объекта.
    service | Service | None | Связанный сервис, если он существует.

    Пример вызова:
    {
      "tool": "GetUrbanObjectsByTerritoryId",
      "arguments": {
        "territory_id": 1,
        "service_type_id": 5,
        "physical_object_type_id": 2
      }
    }

    Пример результата:
    [
      {
        "urban_object_id": 1,
        "physical_object": {
          "name": "Школа №1"
        },
        "object_geometry": {...},
        "service": {
          "name": "Образование"
        }
      }
    ]

    Ошибки:
    - -32001 Not found: territory_id, service_type_id или physical_object_type_id не найдены.
    """,
    tags=["urban_objects", "territories"],
    annotations={"title": "GetUrbanObjectsByTerritoryId", "readOnlyHint": True},
)
async def get_urban_objects_by_territory_id(
    territory_id: Annotated[int, "Идентификатор территории"],
    service_type_id: Annotated[Optional[int], "Фильтр по типу сервиса"] = None,
    physical_object_type_id: Annotated[Optional[int], "Фильтр по типу физического объекта"] = None,
    request: Request = CurrentRequest(),
) -> list[UrbanObject]:
    """Get urban objects by territory identifier."""
    urban_objects_service: UrbanObjectsService = request.state.urban_objects_service
    urban_objects = await urban_objects_service.get_urban_objects_by_territory_id(
        territory_id, service_type_id, physical_object_type_id
    )
    return [UrbanObject.from_dto(urban_object) for urban_object in urban_objects]
