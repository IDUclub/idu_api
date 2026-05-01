"""Integration tests for project-related functional zones are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from idu_api.urban_api.schemas import (
    FunctionalZoneSource,
    FunctionalZoneWithoutGeometry,
    OkResponse,
    ScenarioFunctionalZone,
    ScenarioFunctionalZonePatch,
    ScenarioFunctionalZonePost,
    ScenarioFunctionalZoneWithoutGeometry,
)
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_functional_zone_sources_by_scenario_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    scenario_functional_zone: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/functional_zone_sources method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/functional_zone_sources", headers=headers)
    result = response.json()

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, FunctionalZoneSource, error_message, result_type="list")
        assert any(
            scenario_functional_zone["year"] == item["year"] for item in result
        ), "Response should contain created year."
        assert any(
            scenario_functional_zone["source"] == item["source"] for item in result
        ), "Response should contain created source."
    else:
        assert_response(response, expected_status, FunctionalZoneSource, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_functional_zones_by_scenario_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    scenario_functional_zone: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/functional_zones method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"year": scenario_functional_zone["year"], "source": scenario_functional_zone["source"]}

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/functional_zones", headers=headers, params=params)
    result = response.json()

    # Assert
    assert_response(response, expected_status, GeoJSONResponse, error_message)
    if response.status_code == 200:
        assert len(result["features"]) > 0, "Response should contain at least one feature."
        try:
            ScenarioFunctionalZoneWithoutGeometry(**result["features"][0]["properties"])
        except ValidationError as e:
            pytest.fail(f"Pydantic validation error: {str(e)}")
        assert any(
            scenario_functional_zone["functional_zone_id"] == item["properties"]["functional_zone_id"]
            for item in result["features"]
        ), "Response should contain created functional zone."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_context_functional_zone_sources(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    functional_zone: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/context/functional_zone_sources method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/context/functional_zone_sources", headers=headers)
    result = response.json()

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, FunctionalZoneSource, error_message, result_type="list")
        assert any(functional_zone["year"] == item["year"] for item in result), "Response should contain created year."
        assert any(
            functional_zone["source"] == item["source"] for item in result
        ), "Response should contain created source."
    else:
        assert_response(response, expected_status, FunctionalZoneSource, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_context_functional_zones(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    functional_zone: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/context/functional_zones method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"year": functional_zone["year"], "source": functional_zone["source"]}

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/context/functional_zones", headers=headers, params=params)
    result = response.json()

    # Assert
    assert_response(response, expected_status, GeoJSONResponse, error_message)
    if response.status_code == 200:
        assert len(result["features"]) > 0, "Response should contain at least one feature."
        try:
            FunctionalZoneWithoutGeometry(**result["features"][0]["properties"])
        except ValidationError as e:
            pytest.fail(f"Pydantic validation error: {str(e)}")
        assert any(
            functional_zone["functional_zone_id"] == item["properties"]["functional_zone_id"]
            for item in result["features"]
        ), "Response should contain created functional zone."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (201, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_add_scenario_functional_zones(
    client: AsyncClient,
    scenario_functional_zone_post_req: ScenarioFunctionalZonePost,
    project: dict[str, Any],
    base_regional_scenario: dict[str, Any],
    regional_project: dict[str, Any],
    functional_zone_type: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test POST /scenarios/{scenario_id}/functional_zones method."""

    # Arrange
    if scenario_id_param is None:
        base_scenario_id = (
            project["base_scenario"]["id"] if not is_regional_param else base_regional_scenario["scenario_id"]
        )
        headers = {"Authorization": f"Bearer {superuser_token}"}
        new_scenario = {
            "project_id": project["project_id"] if not is_regional_param else regional_project["project_id"],
            "name": "Test Scenario Name",
            "functional_zone_type_id": functional_zone_type["functional_zone_type_id"],
        }
        response = await client.post(f"/api/v1/scenarios/{base_scenario_id}", json=new_scenario, headers=headers)
        scenario_id = response.json()["scenario_id"]
    else:
        scenario_id = scenario_id_param
    new_functional_zone = scenario_functional_zone_post_req.model_dump()
    new_functional_zone["functional_zone_type_id"] = functional_zone_type["functional_zone_type_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/functional_zones", json=[new_functional_zone], headers=headers
    )

    # Assert
    if response.status_code == 201:
        assert_response(response, expected_status, ScenarioFunctionalZone, error_message, result_type="list")
    else:
        assert_response(response, expected_status, ScenarioFunctionalZone, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_patch_scenario_functional_zone(
    client: AsyncClient,
    scenario_functional_zone_patch_req: ScenarioFunctionalZonePatch,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    scenario_functional_zone: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test PATCH /scenarios/{scenario_id}/functional_zones method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    functional_zone_id = scenario_functional_zone["functional_zone_id"]
    new_functional_zone = scenario_functional_zone_patch_req.model_dump(exclude_unset=True)
    new_functional_zone["functional_zone_type_id"] = scenario_functional_zone["functional_zone_type"]["id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.patch(
        f"/api/v1/scenarios/{scenario_id}/functional_zones/{functional_zone_id}",
        json=new_functional_zone,
        headers=headers,
    )

    # Assert
    assert_response(response, expected_status, ScenarioFunctionalZone, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "regional_scenario", "forbidden", "not_found"],
)
async def test_delete_functional_zones_by_scenario_id(
    client: AsyncClient,
    project: dict[str, Any],
    base_regional_scenario: dict[str, Any],
    regional_project: dict[str, Any],
    functional_zone_type: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test DELETE /scenarios/{scenario_id}/functional_zones method."""

    # Arrange
    if scenario_id_param is None:
        base_scenario_id = (
            project["base_scenario"]["id"] if not is_regional_param else base_regional_scenario["scenario_id"]
        )
        headers = {"Authorization": f"Bearer {superuser_token}"}
        new_scenario = {
            "project_id": project["project_id"] if not is_regional_param else regional_project["project_id"],
            "name": "Test Scenario Name",
            "functional_zone_type_id": functional_zone_type["functional_zone_type_id"],
        }
        response = await client.post(f"/api/v1/scenarios/{base_scenario_id}", json=new_scenario, headers=headers)
        scenario_id = response.json()["scenario_id"]
    else:
        scenario_id = scenario_id_param
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.delete(f"/api/v1/scenarios/{scenario_id}/functional_zones", headers=headers)

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)
