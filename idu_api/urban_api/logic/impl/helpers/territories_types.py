"""Territories types internal logic is defined here."""

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from idu_api.common.db.entities import target_city_types_dict, territory_types_dict
from idu_api.urban_api.dto import TargetCityTypeDTO, TerritoryTypeDTO
from idu_api.urban_api.schemas import TargetCityTypePost, TerritoryTypePost


async def get_territory_types_from_db(conn: AsyncConnection) -> list[TerritoryTypeDTO]:
    """Get all territory type objects."""

    statement = select(territory_types_dict).order_by(territory_types_dict.c.territory_type_id)

    return [TerritoryTypeDTO(**data) for data in (await conn.execute(statement)).mappings().all()]


async def add_territory_type_to_db(
    conn: AsyncConnection,
    territory_type: TerritoryTypePost,
) -> TerritoryTypeDTO:
    """Create territory type object."""

    statement = insert(territory_types_dict).values(**territory_type.model_dump()).returning(territory_types_dict)
    result = (await conn.execute(statement)).mappings().one()

    await conn.commit()

    return TerritoryTypeDTO(**result)


async def get_target_city_types_from_db(conn: AsyncConnection) -> list[TargetCityTypeDTO]:
    """Get all target cities type objects."""

    statement = select(target_city_types_dict).order_by(target_city_types_dict.c.target_city_type_id)

    return [TargetCityTypeDTO(**data) for data in (await conn.execute(statement)).mappings().all()]


async def add_target_city_type_to_db(
    conn: AsyncConnection,
    target_city_type: TargetCityTypePost,
) -> TargetCityTypeDTO:
    """Create target cities type object."""

    statement = insert(target_city_types_dict).values(**target_city_type.model_dump()).returning(target_city_types_dict)
    result = (await conn.execute(statement)).mappings().one()
    await conn.commit()

    return TargetCityTypeDTO(**result)
