"""Integration tests for territory types are defined here."""

from typing import Any

import pytest
from httpx import AsyncClient

from idu_api.urban_api.schemas import TargetCityType, TargetCityTypePost, TerritoryType, TerritoryTypePost
from tests.urban_api.helpers.utils import assert_response

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
async def test_get_territory_types(client: AsyncClient, territory_type: dict[str, Any]):
    """Test GET /territory_types method."""

    # Act
    response = await client.get("/api/v1/territory_types")

    # Assert
    assert_response(response, 200, TerritoryType, result_type="list")
    for res in response.json():
        for k, v in territory_type.items():
            if k in res:
                assert res[k] == v, f"Mismatch for {k}: {res[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message",
    [
        (201, None),
        (409, "уже существует"),
    ],
    ids=["success", "conflict"],
)
async def test_add_territory_type(
    client: AsyncClient,
    territory_type_post_req: TerritoryTypePost,
    expected_status: int,
    error_message: str | None,
):
    """Test POST /territory_types method."""

    # Arrange
    new_type = territory_type_post_req.model_dump()
    new_type["name"] = "new name"

    # Act
    if expected_status == 409:
        await client.post("/api/v1/territory_types", json=new_type)
    response = await client.post("/api/v1/territory_types", json=new_type)

    # Assert
    assert_response(response, expected_status, TerritoryType, error_message)


@pytest.mark.asyncio
async def test_get_target_city_types(client: AsyncClient, target_city_type: dict[str, Any]):
    """Test GET /target_city_types method."""

    # Act
    response = await client.get("/api/v1/target_city_types")

    # Assert
    assert_response(response, 200, TargetCityType, result_type="list")
    for res in response.json():
        for k, v in target_city_type.items():
            if k in res:
                assert res[k] == v, f"Mismatch for {k}: {res[k]} != {v}."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_status, error_message",
    [
        (201, None),
        (409, "уже существует"),
    ],
    ids=["success", "conflict"],
)
async def test_add_target_city_type(
    client: AsyncClient,
    target_city_type_post_req: TargetCityTypePost,
    expected_status: int,
    error_message: str | None,
):
    """Test POST /target_city_types method."""

    # Arrange
    new_type = target_city_type_post_req.model_dump()
    new_type["name"] = "new name"

    # Act
    if expected_status == 409:
        await client.post("/api/v1/target_city_types", json=new_type)
    response = await client.post("/api/v1/target_city_types", json=new_type)

    # Assert
    assert_response(response, expected_status, TargetCityType, error_message)
