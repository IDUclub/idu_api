"""Projects cadastres internal logic is defined here."""

from geoalchemy2.functions import ST_AsEWKB
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from idu_api.common.db.entities import projects_cadastres_data
from idu_api.urban_api.dto import ProjectCadastreDTO, UserDTO
from idu_api.urban_api.logic.impl.helpers.projects_objects import check_project
from idu_api.urban_api.logic.impl.helpers.utils import extract_values_from_model
from idu_api.urban_api.schemas import ProjectCadastrePut


async def get_cadastres_by_project_id_from_db(
    conn: AsyncConnection,
    project_id: int,
    user: UserDTO | None,
) -> list[ProjectCadastreDTO]:
    """Get list of project cadastre objects by project identifier."""

    await check_project(conn, project_id, user, allow_regional=False)

    exclude_columns = ("project_id", "geometry", "centre_point")
    cadastre_columns = [col for col in projects_cadastres_data.c if col.name not in exclude_columns]
    statement = select(
        ST_AsEWKB(projects_cadastres_data.c.geometry).label("geometry"),
        ST_AsEWKB(projects_cadastres_data.c.centre_point).label("centre_point"),
        *cadastre_columns,
    ).where(projects_cadastres_data.c.project_id == project_id)

    result = (await conn.execute(statement)).mappings().all()

    return [ProjectCadastreDTO(**cadastre) for cadastre in result]


async def put_project_cadastres_to_db(
    conn: AsyncConnection,
    cadastres: list[ProjectCadastrePut],
    project_id: int,
    user: UserDTO,
) -> dict:
    """Update list of project cadastre objects."""

    await check_project(conn, project_id, user, to_edit=True, allow_regional=False)

    statement = delete(projects_cadastres_data).where(projects_cadastres_data.c.project_id == project_id)
    await conn.execute(statement)

    async def insert_batch(batch: list[ProjectCadastrePut]):
        insert_values = [{"project_id": project_id, **extract_values_from_model(cadastre)} for cadastre in batch]
        statement = insert(projects_cadastres_data).values(insert_values)
        await conn.execute(statement)

    OBJECTS_NUMBER_TO_INSERT_LIMIT = 1_000
    for batch_start in range(0, len(cadastres), OBJECTS_NUMBER_TO_INSERT_LIMIT):
        batch = cadastres[batch_start : batch_start + OBJECTS_NUMBER_TO_INSERT_LIMIT]
        await insert_batch(batch)
    await conn.commit()

    return {"status": "ok"}


async def delete_cadastres_by_project_id_from_db(conn: AsyncConnection, project_id: int, user: UserDTO) -> dict:
    """Delete cadastres by project identifier."""

    await check_project(conn, project_id, user, to_edit=True, allow_regional=False)

    statement = delete(projects_cadastres_data).where(projects_cadastres_data.c.project_id == project_id)
    await conn.execute(statement)
    await conn.commit()

    return {"status": "ok"}
