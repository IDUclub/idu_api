"""Integration tests for project-related physical objects are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from idu_api.urban_api.schemas import (
    OkResponse,
    PhysicalObject,
    PhysicalObjectPut,
    PhysicalObjectType,
    PhysicalObjectWithGeometryPost,
    ScenarioBuildingPost,
    ScenarioBuildingPut,
    ScenarioPhysicalObject,
    ScenarioPhysicalObjectWithGeometryAttributes,
    ScenarioUrbanObject, BuildingPut,
)
from idu_api.urban_api.schemas.geojson import GeoJSONResponse
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, for_context_param, scenario_id_param",
    [
        (200, None, False, None),
        (200, None, True, None),
        (403, "запрещён", False, None),
        (404, "не найден", False, 1e9),
    ],
    ids=["success_common", "success_context", "forbidden", "not_found"],
)
async def test_get_physical_object_types_by_scenario_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    for_context_param: bool,
    scenario_id_param: int | None,
):
    """Test GET /scenarios/{scenario_id}/physical_object_types method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"for_context": for_context_param}

    # Act
    response = await client.get(
        f"/api/v1/scenarios/{scenario_id}/physical_object_types", headers=headers, params=params
    )
    result = response.json()

    # Assert
    if expected_status == 200:
        assert_response(response, expected_status, PhysicalObjectType, error_message, result_type="list")
        assert any(
            scenario_physical_object["physical_object_type"]["physical_object_type_id"]
            == item["physical_object_type_id"]
            for item in result
        ), "Response should contain at least one physical object type."
    else:
        assert_response(response, expected_status, PhysicalObjectType, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param",
    [
        (200, None, None),
        (400, "пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id", None),
        (403, "запрещён", None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "bad_request", "forbidden", "not_found"],
)
async def test_get_physical_objects_by_scenario_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
):
    """Test GET /scenarios/{scenario_id}/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"physical_object_type_id": scenario_physical_object["physical_object_type"]["physical_object_type_id"]}
    if expected_status == 400:
        physical_object_function = scenario_physical_object["physical_object_type"]["physical_object_function"]
        params["physical_object_function_id"] = physical_object_function["id"]

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/physical_objects", headers=headers, params=params)
    result = response.json()

    # Assert
    if expected_status == 200:
        assert_response(response, expected_status, ScenarioPhysicalObject, error_message, result_type="list")
        assert any(
            scenario_physical_object["physical_object_id"] == item["physical_object_id"] for item in result
        ), "Response should contain created physical_object."
    else:
        assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (200, None, None, True),
        (400, "пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id", None, False),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success_common", "success_regional", "bad_request", "forbidden", "not_found"],
)
async def test_get_physical_objects_with_geometry_by_scenario_id(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/physical_objects_with_geometry method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"physical_object_type_id": scenario_physical_object["physical_object_type"]["physical_object_type_id"]}
    if expected_status == 400 and not is_regional_param:
        physical_object_function = scenario_physical_object["physical_object_type"]["physical_object_function"]
        params["physical_object_function_id"] = physical_object_function["id"]

    # Act
    response = await client.get(
        f"/api/v1/scenarios/{scenario_id}/physical_objects_with_geometry", headers=headers, params=params
    )
    result = response.json()

    # Assert
    assert_response(response, expected_status, GeoJSONResponse, error_message)
    if response.status_code == 200:
        assert len(result["features"]) > 0, "Response should contain at least one feature."
        try:
            ScenarioPhysicalObjectWithGeometryAttributes(**result["features"][0]["properties"])
        except ValidationError as e:
            pytest.fail(f"Pydantic validation error: {str(e)}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id", None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "bad_request", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_context_physical_objects(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/context/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"physical_object_type_id": physical_object["physical_object_type"]["physical_object_type_id"]}
    if expected_status == 400 and not is_regional_param:
        physical_object_function = physical_object["physical_object_type"]["physical_object_function"]
        params["physical_object_function_id"] = physical_object_function["id"]

    # Act
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/context/physical_objects", headers=headers, params=params)
    result = response.json()

    # Assert
    if expected_status == 200:
        assert_response(response, expected_status, PhysicalObject, error_message, result_type="list")
        assert any(
            physical_object["physical_object_id"] == item["physical_object_id"] for item in result
        ), "Response should contain created physical_object."
    else:
        assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_regional_param",
    [
        (200, None, None, False),
        (400, "пожалуйста, выберите либо physical_object_type_id, либо physical_object_function_id", None, False),
        (400, "этот метод недоступен в региональном сценарии", None, True),
        (403, "запрещён", None, False),
        (404, "не найден", 1e9, False),
    ],
    ids=["success", "bad_request", "regional_scenario", "forbidden", "not_found"],
)
async def test_get_context_physical_objects_with_geometry(
    client: AsyncClient,
    scenario: dict[str, Any],
    regional_scenario: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_regional_param: bool,
):
    """Test GET /scenarios/{scenario_id}/context/physical_objects_with_geometry method."""

    # Arrange
    scenario_id = scenario_id_param or (
        regional_scenario["scenario_id"] if is_regional_param else scenario["scenario_id"]
    )
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"physical_object_type_id": physical_object["physical_object_type"]["physical_object_type_id"]}
    if expected_status == 400 and not is_regional_param:
        physical_object_function = physical_object["physical_object_type"]["physical_object_function"]
        params["physical_object_function_id"] = physical_object_function["id"]

    # Act
    response = await client.get(
        f"/api/v1/scenarios/{scenario_id}/context/physical_objects_with_geometry", headers=headers, params=params
    )
    result = response.json()

    # Assert
    assert_response(response, expected_status, GeoJSONResponse, error_message)
    if response.status_code == 200:
        assert len(result["features"]) > 0, "Response should contain at least one feature."
        try:
            PhysicalObject(**result["features"][0]["properties"])
        except ValidationError as e:
            pytest.fail(f"Pydantic validation error: {str(e)}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param",
    [
        (201, None, None),
        (403, "запрещён", None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "forbidden", "not_found"],
)
async def test_add_physical_object_with_geometry(
    client: AsyncClient,
    physical_object_with_geometry_post_req: PhysicalObjectWithGeometryPost,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    city: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
):
    """Test POST /scenarios/{scenario_id}/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    new_object = physical_object_with_geometry_post_req.model_dump()
    new_object["physical_object_type_id"] = scenario_physical_object["physical_object_type"]["physical_object_type_id"]
    new_object["territory_id"] = city["territory_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/physical_objects",
        json=new_object,
        headers=headers,
    )

    # Assert
    assert_response(response, expected_status, ScenarioUrbanObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
        (409, "уже изменена или удалена для этого сценария", None, False),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found", "conflict"],
)
async def test_put_scenario_physical_object(
    client: AsyncClient,
    physical_object_put_req: PhysicalObjectPut,
    project: dict[str, Any],
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    functional_zone_type: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test PUT /scenarios/{scenario_id}/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    physical_object_id = (
        scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    )
    new_object = physical_object_put_req.model_dump()
    new_object["physical_object_type_id"] = scenario_physical_object["physical_object_type"]["physical_object_type_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"is_scenario_object": is_scenario_param}

    # Act
    if expected_status == 409:
        await client.put(
            f"/api/v1/scenarios/{scenario_id}/physical_objects/{physical_object_id}",
            json=new_object,
            headers=headers,
            params=params,
        )
    response = await client.put(
        f"/api/v1/scenarios/{scenario_id}/physical_objects/{physical_object_id}",
        json=new_object,
        headers=headers,
        params=params,
    )

    # Assert
    assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
        (409, "уже изменена или удалена для этого сценария", None, False),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found", "conflict"],
)
async def test_patch_scenario_physical_object(
    client: AsyncClient,
    physical_object_put_req: PhysicalObjectPut,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    project: dict[str, Any],
    functional_zone_type: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test PATCH /scenarios/{scenario_id}/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    physical_object_id = (
        scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    )
    new_object = physical_object_put_req.model_dump()
    new_object["physical_object_type_id"] = scenario_physical_object["physical_object_type"]["physical_object_type_id"]
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}
    params = {"is_scenario_object": is_scenario_param}

    # Act
    if expected_status == 409:
        await client.patch(
            f"/api/v1/scenarios/{scenario_id}/physical_objects/{physical_object_id}",
            json=new_object,
            headers=headers,
            params=params,
        )
    response = await client.patch(
        f"/api/v1/scenarios/{scenario_id}/physical_objects/{physical_object_id}",
        json=new_object,
        headers=headers,
        params=params,
    )

    # Assert
    assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found"],
)
async def test_delete_physical_object(
    client: AsyncClient,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test DELETE /scenarios/{scenario_id}/physical_objects method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    pid = scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    params = {"is_scenario_object": is_scenario_param}
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.delete(
        f"/api/v1/scenarios/{scenario_id}/physical_objects/{pid}",
        headers=headers,
        params=params,
    )

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (201, None, None, True),
        (201, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
        (409, "уже существует", None, True),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found", "conflict"],
)
async def test_add_scenario_building(
    client: AsyncClient,
    scenario_building_post_req: ScenarioBuildingPost,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test POST /scenarios/{scenario_id}/buildings method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    pid = scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    new_building = scenario_building_post_req.model_dump()
    new_building["physical_object_id"] = pid
    new_building["is_scenario_object"] = is_scenario_param
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    if expected_status == 409:
        await client.post(f"/api/v1/scenarios/{scenario_id}/buildings", json=new_building, headers=headers)
    response = await client.post(f"/api/v1/scenarios/{scenario_id}/buildings", json=new_building, headers=headers)

    # Assert
    assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found"],
)
async def test_put_scenario_building(
    client: AsyncClient,
    scenario_building_put_req: ScenarioBuildingPut,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test PUT /scenarios/{scenario_id}/buildings method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    pid = scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    new_building = scenario_building_put_req.model_dump()
    new_building["physical_object_id"] = pid
    new_building["is_scenario_object"] = is_scenario_param
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.put(f"/api/v1/scenarios/{scenario_id}/buildings", json=new_building, headers=headers)

    # Assert
    assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found"],
)
async def test_patch_scenario_building(
    client: AsyncClient,
    building_put_req: BuildingPut,
    scenario_building_put_req: ScenarioBuildingPut,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test PATCH /scenarios/{scenario_id}/buildings method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    pid = scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    if not is_scenario_param:
        new_building = building_put_req.model_dump()
        new_building["physical_object_id"] = pid
        response = await client.put("/api/v1/buildings", json=new_building)
        building_id = response.json()["building"]["id"]
    else:
        new_building = scenario_building_put_req.model_dump()
        new_building["physical_object_id"] = pid
        new_building["is_scenario_object"] = is_scenario_param
        headers = {"Authorization": f"Bearer {superuser_token}"}
        response = await client.put(
            f"/api/v1/scenarios/{scenario['scenario_id']}/buildings", json=new_building, headers=headers
        )
        building_id = response.json()["building"]["id"]
    params = {"is_scenario_object": is_scenario_param}
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.patch(
        f"/api/v1/scenarios/{scenario_id}/buildings/{building_id}",
        json=new_building,
        params=params,
        headers=headers,
    )

    # Assert
    assert_response(response, expected_status, ScenarioPhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, scenario_id_param, is_scenario_param",
    [
        (200, None, None, True),
        (200, None, None, False),
        (403, "запрещён", None, True),
        (404, "не найден", 1e9, True),
    ],
    ids=["success_1", "success_2", "forbidden", "not_found"],
)
async def test_delete_scenario_building(
    client: AsyncClient,
    building_put_req: BuildingPut,
    scenario_building_put_req: ScenarioBuildingPut,
    scenario: dict[str, Any],
    scenario_physical_object: dict[str, Any],
    physical_object: dict[str, Any],
    valid_token: str,
    superuser_token: str,
    expected_status: int,
    error_message: str | None,
    scenario_id_param: int | None,
    is_scenario_param: bool,
):
    """Test DELETE /scenarios/{scenario_id}/buildings method."""

    # Arrange
    scenario_id = scenario_id_param or scenario["scenario_id"]
    pid = scenario_physical_object["physical_object_id"] if is_scenario_param else physical_object["physical_object_id"]
    if not is_scenario_param:
        new_building = building_put_req.model_dump()
        new_building["physical_object_id"] = pid
        response = await client.post("/api/v1/buildings", json=new_building)
        building_id = response.json()["building"]["id"]
    else:
        new_building = scenario_building_put_req.model_dump()
        new_building["physical_object_id"] = pid
        new_building["is_scenario_object"] = is_scenario_param
        headers = {"Authorization": f"Bearer {superuser_token}"}
        response = await client.put(
            f"/api/v1/scenarios/{scenario['scenario_id']}/buildings", json=new_building, headers=headers
        )
        building_id = response.json()["building"]["id"]
    params = {"is_scenario_object": is_scenario_param}
    headers = {"Authorization": f"Bearer {valid_token if expected_status == 403 else superuser_token}"}

    # Act
    response = await client.delete(
        f"/api/v1/scenarios/{scenario_id}/buildings/{building_id}",
        params=params,
        headers=headers,
    )

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)
