"""Integration tests for physical objects are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient

from idu_api.urban_api.schemas import (
    BuildingPost,
    BuildingPut,
    ObjectGeometry,
    OkResponse,
    PhysicalObject,
    PhysicalObjectPatch,
    PhysicalObjectPost,
    PhysicalObjectWithGeometry,
    PhysicalObjectWithGeometryPost,
    Service,
    ServiceWithGeometry,
    UrbanObject,
)
from idu_api.urban_api.schemas.geometries import AllPossibleGeometry
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_physical_object_by_id(
    client: AsyncClient,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test GET /physical_object/{physical_object_id} method."""

    # Arrange
    physical_object_id = object_id_param or physical_object["physical_object_id"]

    # Act
    response = await client.get(f"/api/v1/physical_object/{physical_object_id}")
    result = response.json()

    # Assert
    assert_response(response, expected_status, PhysicalObject, error_message)
    if response.status_code == 200:
        for k, v in physical_object.items():
            if k in result and k not in ("physical_object_type", "territories"):
                assert result[k] == v, f"Mismatch for {k}: {result[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, type_id_param, territory_id_param",
    [
        (201, None, None, None),
        (404, "отсутствует в таблице", 1e9, 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_add_physical_object_with_geometry(
    client: AsyncClient,
    physical_object_with_geometry_post_req: PhysicalObjectWithGeometryPost,
    physical_object_type: dict[str, Any],
    city: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    type_id_param: int | None,
    territory_id_param: int | None,
):
    """Test POST /physical_objects method."""

    # Arrange
    new_object = physical_object_with_geometry_post_req.model_dump()
    new_object["physical_object_type_id"] = type_id_param or physical_object_type["physical_object_type_id"]
    new_object["territory_id"] = territory_id_param or city["territory_id"]

    # Act
    response = await client.post("/api/v1/physical_objects", json=new_object)

    # Assert
    assert_response(response, expected_status, UrbanObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_patch_physical_object(
    client: AsyncClient,
    physical_object_patch_req: PhysicalObjectPatch,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test PATCH /physical_objects method."""

    # Arrange
    new_object = physical_object_patch_req.model_dump()
    new_object["physical_object_type_id"] = physical_object["physical_object_type"]["physical_object_type_id"]
    physical_object_id = object_id_param or physical_object["physical_object_id"]

    # Act
    response = await client.patch(f"/api/v1/physical_objects/{physical_object_id}", json=new_object)

    # Assert
    assert_response(response, expected_status, PhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_delete_physical_object(
    client: AsyncClient,
    physical_object_with_geometry_post_req: PhysicalObjectWithGeometryPost,
    physical_object_type: dict[str, Any],
    city: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test DELETE /physical_objects method."""

    # Arrange
    new_object = physical_object_with_geometry_post_req.model_dump()
    new_object["physical_object_type_id"] = physical_object_type["physical_object_type_id"]
    new_object["territory_id"] = city["territory_id"]

    # Act
    if object_id_param is None:
        response = await client.post("/api/v1/physical_objects", json=new_object)
        physical_object_id = response.json()["physical_object"]["physical_object_id"]
        response = await client.delete(f"/api/v1/physical_objects/{physical_object_id}")
    else:
        response = await client.delete(f"/api/v1/physical_objects/{object_id_param}")

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (201, None, None),
        (404, "отсутствует в таблице", 1e9),
        (409, "уже существует", None),
    ],
    ids=["success", "not_found", "conflict"],
)
async def test_add_building(
    client: AsyncClient,
    building_post_req: BuildingPost,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test POST /buildings method."""

    # Arrange
    new_object = building_post_req.model_dump()
    new_object["physical_object_id"] = object_id_param or physical_object["physical_object_id"]

    # Act
    if expected_status == 409:
        await client.post("/api/v1/buildings", json=new_object)
    response = await client.post("/api/v1/buildings", json=new_object)
    result = response.json()

    # Assert
    assert_response(response, expected_status, PhysicalObject, error_message)
    if response.status_code == 201:
        for k, v in new_object.items():
            if k in result["building"]:
                assert result["building"][k] == v, f"Mismatch for {k}: {result[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "отсутствует в таблице", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_put_building(
    client: AsyncClient,
    building_put_req: BuildingPut,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test PUT /buildings method."""

    # Arrange
    new_object = building_put_req.model_dump()
    new_object["physical_object_id"] = object_id_param or physical_object["physical_object_id"]

    # Act
    response = await client.put("/api/v1/buildings", json=new_object)
    result = response.json()

    # Assert
    assert_response(response, expected_status, PhysicalObject, error_message)
    if response.status_code == 200:
        for k, v in new_object.items():
            if k in result["building"]:
                assert result["building"][k] == v, f"Mismatch for {k}: {result[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, building_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_patch_building(
    client: AsyncClient,
    building_put_req: BuildingPut,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    building_id_param: int | None,
):
    """Test PATCH /buildings method."""

    # Arrange
    new_object = building_put_req.model_dump()
    new_object["physical_object_id"] = physical_object["physical_object_id"]
    await client.put("/api/v1/buildings", json=new_object)

    # Act
    if building_id_param is None:
        response = await client.get(f"/api/v1/physical_object/{new_object['physical_object_id']}")
        building_id = response.json()["building"]["id"]
        response = await client.patch(f"/api/v1/buildings/{building_id}", json=new_object)
    else:
        response = await client.patch(f"/api/v1/buildings/{building_id_param}", json=new_object)

    # Assert
    assert_response(response, expected_status, PhysicalObject, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, building_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_delete_building(
    client: AsyncClient,
    building_put_req: BuildingPut,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    building_id_param: int | None,
):
    """Test DELETE /buildings method."""

    # Arrange
    new_object = building_put_req.model_dump()
    new_object["physical_object_id"] = physical_object["physical_object_id"]
    await client.put("/api/v1/buildings", json=new_object)

    # Act
    if building_id_param is None:
        response = await client.get(f"/api/v1/physical_object/{new_object['physical_object_id']}")
        building_id = response.json()["building"]["id"]
        response = await client.delete(f"/api/v1/buildings/{building_id}")
    else:
        response = await client.delete(f"/api/v1/buildings/{building_id_param}")

    # Assert
    assert_response(response, expected_status, OkResponse, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_services_by_physical_object_id(
    client: AsyncClient,
    physical_object: dict[str, Any],
    service: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test GET /physical_objects/{physical_object_id}/services method."""

    # Arrange
    physical_object_id = object_id_param or physical_object["physical_object_id"]

    # Act
    response = await client.get(f"/api/v1/physical_objects/{physical_object_id}/services")

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, Service, error_message, result_type="list")
        assert any(
            service["service_id"] == item["service_id"] for item in response.json()
        ), "Expected service was не найден in result."
    else:
        assert_response(response, expected_status, Service, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_services_with_geometry_by_physical_object_id(
    client: AsyncClient,
    physical_object: dict[str, Any],
    service: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test GET /physical_objects/{physical_object_id}/services_with_geometry method."""

    # Arrange
    physical_object_id = object_id_param or physical_object["physical_object_id"]

    # Act
    response = await client.get(f"/api/v1/physical_objects/{physical_object_id}/services_with_geometry")

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, ServiceWithGeometry, error_message, result_type="list")
        assert any(
            service["service_id"] == item["service_id"] for item in response.json()
        ), "Expected service was не найден in result."
    else:
        assert_response(response, expected_status, ServiceWithGeometry, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, object_id_param",
    [
        (200, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_get_physical_object_geometries(
    client: AsyncClient,
    physical_object: dict[str, Any],
    object_geometry: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    object_id_param: int | None,
):
    """Test GET /physical_objects/{physical_object_id}/geometries method."""

    # Arrange
    physical_object_id = object_id_param or physical_object["physical_object_id"]
    object_geometry_id = object_geometry["object_geometry_id"]

    # Act
    response = await client.get(f"/api/v1/physical_objects/{physical_object_id}/geometries")

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, ObjectGeometry, error_message, result_type="list")
        assert any(
            object_geometry_id == item["object_geometry_id"] for item in response.json()
        ), "Expected geometry was не найден in result."
    else:
        assert_response(response, expected_status, ObjectGeometry, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, geometry_param",
    [
        (200, None, AllPossibleGeometry(type="Point", coordinates=[30.22, 59.86], geometries=None)),
        (400, None, AllPossibleGeometry(type="Polygon", coordinates=[30.22, 59.86], geometries=None)),
    ],
    ids=["success", "bad_request"],
)
async def test_get_physical_objects_around_geometry(
    client: AsyncClient,
    physical_object: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    geometry_param: AllPossibleGeometry,
):
    """Test POST /physical_objects/around."""

    # Arrange
    physical_object_id = physical_object["physical_object_id"]

    # Act
    response = await client.post("/api/v1/physical_objects/around", json=geometry_param.model_dump())

    # Assert
    if response.status_code == 200:
        assert_response(response, expected_status, PhysicalObjectWithGeometry, error_message, result_type="list")
        assert any(
            physical_object_id == item["physical_object_id"] for item in response.json()
        ), "Expected physical object was не найден in result."
    else:
        assert_response(response, expected_status, PhysicalObjectWithGeometry, error_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message, geometry_id_param",
    [
        (201, None, None),
        (404, "не найден", 1e9),
    ],
    ids=["success", "not_found"],
)
async def test_add_physical_object_to_object_geometry(
    client: AsyncClient,
    physical_object_post_req: PhysicalObjectPost,
    physical_object: dict[str, Any],
    object_geometry: dict[str, Any],
    expected_status: int,
    error_message: str | None,
    geometry_id_param: int | None,
):
    """Test POST /physical_objects/{object_geometry_id} method."""

    # Arrange
    object_geometry_id = geometry_id_param or object_geometry["object_geometry_id"]
    json_data = physical_object_post_req.model_dump()
    json_data["physical_object_type_id"] = physical_object["physical_object_type"]["physical_object_type_id"]

    # Act
    response = await client.post(f"/api/v1/physical_objects/{object_geometry_id}", json=json_data)

    # Assert
    assert_response(response, expected_status, UrbanObject, error_message)
