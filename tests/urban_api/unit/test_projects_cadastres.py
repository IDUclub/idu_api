from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from geoalchemy2.functions import ST_AsEWKB
from sqlalchemy import delete, insert, select

from idu_api.common.db.entities import projects_cadastres_data
from idu_api.urban_api.dto import ProjectCadastreDTO, UserDTO
from idu_api.urban_api.exceptions.logic.projects import NotAllowedInRegionalProject
from idu_api.urban_api.logic.impl.helpers.projects_cadastres import (
    delete_cadastres_by_project_id_from_db,
    get_cadastres_by_project_id_from_db,
    put_project_cadastres_to_db,
)
from idu_api.urban_api.logic.impl.helpers.utils import extract_values_from_model
from idu_api.urban_api.schemas import ProjectCadastrePut
from tests.urban_api.helpers import MockConnection


@pytest.mark.asyncio
async def test_get_cadastres_by_project_id_from_db(mock_conn: MockConnection):
    """Test the get_cadastres_by_project_id_from_db function."""

    # Arrange
    project_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    exclude_columns = ("project_id", "geometry", "centre_point")
    cadastre_columns = [col for col in projects_cadastres_data.c if col.name not in exclude_columns]
    statement = select(
        ST_AsEWKB(projects_cadastres_data.c.geometry).label("geometry"),
        ST_AsEWKB(projects_cadastres_data.c.centre_point).label("centre_point"),
        *cadastre_columns,
    ).where(projects_cadastres_data.c.project_id == project_id)

    # Act
    with pytest.raises(NotAllowedInRegionalProject):
        await get_cadastres_by_project_id_from_db(mock_conn, project_id, user)
    with patch("idu_api.urban_api.logic.impl.helpers.projects_cadastres.check_project") as mock_check:
        result = await get_cadastres_by_project_id_from_db(mock_conn, project_id, user)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(isinstance(item, ProjectCadastreDTO) for item in result), "Each item should be a ProjectCadastreDTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_check.assert_called_once_with(mock_conn, project_id, user, allow_regional=False)


@pytest.mark.asyncio
@patch("idu_api.urban_api.logic.impl.helpers.projects_cadastres.check_project")
async def test_put_project_cadastres_to_db(
    mock_check: AsyncMock, mock_conn: MockConnection, project_cadastre_put_req: ProjectCadastrePut
):
    """Test the put_project_cadastres_to_db function."""

    # Arrange
    project_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    delete_statement = delete(projects_cadastres_data).where(projects_cadastres_data.c.project_id == project_id)
    insert_statement = insert(projects_cadastres_data).values(
        [{"project_id": project_id, **extract_values_from_model(project_cadastre_put_req)}]
    )

    # Act
    result = await put_project_cadastres_to_db(mock_conn, [project_cadastre_put_req], project_id, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_any_call(str(delete_statement))
    mock_conn.execute_mock.assert_any_call(str(insert_statement))
    mock_conn.commit_mock.assert_called_once()
    mock_check.assert_called_once_with(mock_conn, project_id, user, to_edit=True, allow_regional=False)


@pytest.mark.asyncio
@patch("idu_api.urban_api.logic.impl.helpers.projects_cadastres.check_project")
async def test_delete_cadastres_by_project_id_from_db(mock_check: AsyncMock, mock_conn: MockConnection):
    """Test the delete_cadastres_by_project_id_from_db function."""

    # Arrange
    project_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    delete_statement = delete(projects_cadastres_data).where(projects_cadastres_data.c.project_id == project_id)

    # Act
    result = await delete_cadastres_by_project_id_from_db(mock_conn, project_id, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_called_once_with(str(delete_statement))
    mock_conn.commit_mock.assert_called_once()
    mock_check.assert_any_call(mock_conn, project_id, user, to_edit=True, allow_regional=False)
