"""Integration tests for scenarios-related scenarios are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient

from idu_api.urban_api.schemas import (
    OkResponse,
    Scenario,
    ScenarioPatch,
    ScenarioPost,
)
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (200, None, None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success_common", "success_regional", "forbidden", "not_found"],
)
async def test_get_scenario_by_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id} method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}", headers=headers)

    # Assert
    assert_response(response, expected_status, Scenario, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (201, None, None, False),
        (201, None, None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success_common", "success_regional", "forbidden", "not_found"],
)
async def test_copy_scenario(
    client: AsyncClient,
    scenario_post_req: ScenarioPost,
    project: dict[str, Any],
    regional_scenario: dict[str, Any],
    regional_project: dict[str, Any],
    functional_zone_type: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    valid_token: str,
    superuser_token: str,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test POST /scenarios/{scenario_id} method."""

    # Arrange
    new_scenario = scenario_post_req.model_dump()
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else project["base_scenario"]["id"]
    )
    new_scenario["project_id"] = regional_project["project_id"] if is_regional_param else project["project_id"]
    new_scenario["functional_zone_type_id"] = functional_zone_type["functional_zone_type_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.post(f"/api/v1/scenarios/{scenario_id}", json=new_scenario, headers=headers)

    # Assert
    assert_response(response, expected_status, Scenario, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param",
    [
        (200, None, None),
        (403, "запрещён", None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "forbidden", "not_found"],
)
async def test_patch_scenario(
    client: AsyncClient,
    scenario_patch_req: ScenarioPatch,
    project: dict[str, Any],
    functional_zone_type: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    valid_token: str,
    superuser_token: str,
    scenario_id_param: int | None,
):
    """Test PATCH /scenarios/{scenario_id} method."""

    # Arrange
    scenario_id = scenario_id_param or project["base_scenario"]["id"]
    new_scenario = scenario_patch_req.model_dump(exclude_unset=True)
    new_scenario["functional_zone_type_id"] = functional_zone_type["functional_zone_type_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.patch(f"/api/v1/scenarios/{scenario_id}", json=new_scenario, headers=headers)

    # Assert
    assert_response(response, expected_status, Scenario, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param",
    [
        (200, None, None),
        (403, "запрещён", None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_authenticated", "not_found"],
)
async def test_delete_scenario(
    client: AsyncClient,
    scenario: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    valid_token: str,
    superuser_token: str,
    scenario_id_param: int | None,
):
    """Test DELETE /scenarios/{scenario_id} method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.delete(f"/api/v1/scenarios/{scenario_id}", headers=headers)

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)
