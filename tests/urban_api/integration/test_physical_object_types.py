"""Integration tests for physical objects types are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient

from idu_api.urban_api.schemas import (
    OkResponse,
    PhysicalObjectFunction,
    PhysicalObjectFunctionPost,
    PhysicalObjectFunctionPut,
    PhysicalObjectsTypesHierarchy,
    PhysicalObjectType,
    PhysicalObjectTypePatch,
    PhysicalObjectTypePost,
    ServiceType,
)
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
async def test_get_physical_object_types(
    client: AsyncClient,
    physical_object_function: dict[str, Any],
    physical_object_type: dict[str, Any],
):
    """Test GET /physical_object_types method."""

    # Arrange
    params = {
        "physical_object_function_id": physical_object_function["physical_object_function_id"],
        "name": physical_object_type["name"],
    }

    # Act
    response = await client.get("/api/v1/physical_object_types", params=params)

    # Assert
    assert_response(response, 200, PhysicalObjectType, result_type="list")
    for res in response.json():
        for k, v in physical_object_type.items():
            if k in res:
                assert res[k] == v, f"Mismatch for {k}: {res[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, function_id_param",
    [
        (201, None, None),
        (404, "отсутствует в таблице", 1e9),
        (409, "уже существует", None),
    ],
    ids=["success", "not_found", "conflict"],
)
async def test_add_physical_object_type(
    client: AsyncClient,
    physical_object_type_post_req: PhysicalObjectTypePost,
    physical_object_function: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    function_id_param: int | None,
):
    """Test POST /physical_object_types method."""

    # Arrange
    new_type = physical_object_type_post_req.model_dump()
    new_type["name"] = "new name" if expected_status != 404 else "failed name"
    new_type["physical_object_function_id"] = (
        function_id_param or physical_object_function["physical_object_function_id"]
    )

    # Act
    if expected_status == 409:
        await client.post("/api/v1/physical_object_types", json=new_type)
    response = await client.post("/api/v1/physical_object_types", json=new_type)

    # Assert
    assert_response(response, expected_status, PhysicalObjectType, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, type_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
        (409, "уже существует", None),
    ],
    ids=["success", "not_found", "conflict"],
)
async def test_patch_physical_object_type(
    client: AsyncClient,
    physical_object_type_patch_req: PhysicalObjectTypePatch,
    physical_object_function: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    type_id_param: int | None,
):
    """Test PATCH /physical_object_types method."""

    # Arrange
    new_type = physical_object_type_patch_req.model_dump()
    new_type["physical_object_function_id"] = physical_object_function["physical_object_function_id"]
    response = await client.post("/api/v1/physical_object_types", json=new_type)
    physical_object_type_id = type_id_param or response.json().get("physical_object_type_id")

    # Act
    if expected_status == 409:
        new_type["name"] = "conflict type"
        await client.post("/api/v1/physical_object_types", json=new_type)
    response = await client.patch(f"/api/v1/physical_object_types/{physical_object_type_id}", json=new_type)

    # Assert
    assert_response(response, expected_status, PhysicalObjectType, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, type_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_delete_physical_object_type(
    client: AsyncClient,
    physical_object_type: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    type_id_param: int | None,
):
    """Test DELETE /physical_object_types method."""

    # Arrange
    type_id = type_id_param or physical_object_type["physical_object_type_id"]

    # Act
    response = await client.delete(f"/api/v1/physical_object_types/{type_id}")

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, parent_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_physical_object_functions_by_parent_id(
    client: AsyncClient,
    physical_object_function: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    parent_id_param: int | None,
):
    """Test GET /physical_object_functions_by_parent method."""

    # Arrange
    params = {"get_all_subtree": True, "name": "test"}
    if parent_id_param is not None:
        params["parent_id"] = parent_id_param

    # Act
    response = await client.get("/api/v1/physical_object_functions_by_parent", params=params)

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, PhysicalObjectFunction, result_type="list")
        for res in response.json():
            for k, v in physical_object_function.items():
                if k in res:
                    assert res[k] == v, f"Mismatch for {k}: {res[k]} != {v}."
    else:
        assert_response(response, expected_status, PhysicalObjectFunction, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, parent_id_param",
    [
        (201, None, None),
        (404, "не найден", 1e9),
        (409, "уже существует", None),
    ],
    ids=["success", "not_found", "conflict"],
)
async def test_add_physical_object_function(
    client: AsyncClient,
    physical_object_function_post_req: PhysicalObjectFunctionPost,
    expected_status: int,
    error_message: str | None,
    parent_id_param: int | None,
):
    """Test POST /physical_object_functions method."""

    # Arrange
    new_function = physical_object_function_post_req.model_dump()
    new_function["name"] = "new name" if expected_status != 404 else "failed name"
    new_function["parent_id"] = parent_id_param

    # Act
    if expected_status == 409:
        await client.post("/api/v1/physical_object_functions", json=new_function)
    response = await client.post("/api/v1/physical_object_functions", json=new_function)

    # Assert
    assert_response(response, expected_status, PhysicalObjectFunction, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, parent_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_put_physical_object_function(
    client: AsyncClient,
    physical_object_function_put_req: PhysicalObjectFunctionPut,
    expected_status: int,
    error_message: str | None,
    parent_id_param: int | None,
):
    """Test POST /physical_object_functions method."""

    # Arrange
    new_function = physical_object_function_put_req.model_dump()
    new_function["name"] = "new name" if expected_status != 404 else "failed name"
    new_function["parent_id"] = parent_id_param

    # Act
    response = await client.put("/api/v1/physical_object_functions", json=new_function)

    # Assert
    assert_response(response, expected_status, PhysicalObjectFunction, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, function_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
        (409, "уже существует", None),
    ],
    ids=["success", "not_found", "conflict"],
)
async def test_patch_physical_object_function(
    client: AsyncClient,
    physical_object_function_put_req: PhysicalObjectFunctionPut,
    expected_status: int,
    error_message: str | None,
    function_id_param: int | None,
):
    """Test PATCH /physical_object_functions method."""

    # Arrange
    new_function = physical_object_function_put_req.model_dump()
    new_function["parent_id"] = None
    response = await client.post("/api/v1/physical_object_functions", json=new_function)
    physical_object_function_id = function_id_param or response.json().get("physical_object_function_id")

    # Act
    if expected_status == 409:
        new_function["name"] = "conflict function"
        await client.post("/api/v1/physical_object_functions", json=new_function)
    response = await client.patch(f"/api/v1/physical_object_functions/{physical_object_function_id}", json=new_function)

    # Assert
    assert_response(response, expected_status, PhysicalObjectFunction, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, function_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_delete_physical_object_function(
    client: AsyncClient,
    physical_object_function: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    function_id_param: int | None,
):
    """Test DELETE /physical_object_functions method."""

    # Arrange
    function_id = function_id_param or physical_object_function["physical_object_function_id"]

    # Act
    response = await client.delete(f"/api/v1/physical_object_functions/{function_id}")

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, ids_param",
    [
        (200, None, None),
        (400, None, "1.2.3"),
        (404, "не найден", str(10**9)),
    ],
    ids=["success", "bad_request", "not_found"],
)
async def test_get_physical_object_types_hierarchy(
    client: AsyncClient,
    physical_object_function: dict[str, Any],
    physical_object_type: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    ids_param: str | None,
):
    """Test GET /physical_object_types/hierarchy method."""

    # Arrange
    params = {}
    if ids_param is not None:
        params["physical_object_types_ids"] = ids_param

    # Act
    response = await client.get("/api/v1/physical_object_types/hierarchy", params=params)

    # Assert
    if expected_status == 200:
        assert_response(response, expected_status, PhysicalObjectsTypesHierarchy, error_message, result_type="list")
        assert len(response.json()) > 0, "Hierarchy should contain at least one physical object type."
    else:
        assert_response(response, expected_status, PhysicalObjectsTypesHierarchy, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, type_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_service_types(
    client: AsyncClient,
    physical_object_type: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    type_id_param: str | None,
):
    """Test GET /physical_object_types/{physical_object_type_id}/service_types method."""

    # Arrange
    physical_object_type_id = type_id_param or physical_object_type["physical_object_type_id"]

    # Act
    response = await client.get(f"/api/v1/physical_object_types/{physical_object_type_id}/service_types")

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, ServiceType, result_type="list")
    else:
        assert_response(response, expected_status, ServiceType)
