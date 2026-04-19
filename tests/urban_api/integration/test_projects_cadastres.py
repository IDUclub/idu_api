"""Integration tests for project-related cadastres are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from idu_api.urban_api.schemas import OkResponse, ProjectCadastreAttributes, ProjectCadastrePut
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, project_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном проекте", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_project", "forbidden", "not_found"],
)
async def test_get_cadastres_by_project_id(
    client: AsyncClient,
    project: dict[str, Any],
    regional_project: dict[str, Any],
    project_cadastre: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    project_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /projects/{project_id}/cadastres method."""

    # Arrange
    project_id = project_id_param or (regional_project["project_id"] if is_regional_param else project["project_id"])
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.get(f"/api/v1/projects/{project_id}/cadastres", headers=headers)
    result = response.json()

    # Assert
    assert_response(response, expected_status, GeoJSONResponse, error_message)
    if response.status_code == 200:
        assert len(result["features"]) > 0, "Response should contain at least one feature."
        try:
            ProjectCadastreAttributes(**result["features"][0]["properties"])
        except ValidationError as e:
            pytest.fail(f"Pydantic validation error: {str(e)}")
        assert any(
            project_cadastre["project_cadastre_id"] == item["properties"]["project_cadastre_id"]
            for item in result["features"]
        ), "Response should contain created cadastre."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, project_id_param, is_regional_param",
    [
        (201, None, None, False),
        (400, "этот метод недоступен в региональном проекте", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_project", "forbidden", "not_found"],
)
async def test_put_project_cadastres(
    client: AsyncClient,
    project_cadastre_put_req: ProjectCadastrePut,
    project: dict[str, Any],
    regional_project: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    project_id_param: int | None,
    is_regional_param: bool,
):
    """Test POST /projects/{project_id}/cadastres method."""

    # Arrange
    project_id = project_id_param or (regional_project["project_id"] if is_regional_param else project["project_id"])
    new_cadastre = project_cadastre_put_req.model_dump()
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.put(f"/api/v1/projects/{project_id}/cadastres", json=[new_cadastre], headers=headers)

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, project_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном проекте", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_project", "forbidden", "not_found"],
)
async def test_delete_cadastres_by_project_id(
    client: AsyncClient,
    project: dict[str, Any],
    regional_project: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    project_id_param: int | None,
    is_regional_param: bool,
):
    """Test DELETE /projects/{project_id}/cadastres method."""

    # Arrange
    project_id = project_id_param or (regional_project["project_id"] if is_regional_param else project["project_id"])
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.delete(f"/api/v1/projects/{project_id}/cadastres", headers=headers)

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)
