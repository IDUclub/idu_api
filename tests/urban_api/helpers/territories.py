"""All fixtures for territories tests are defined here."""

from typing import Any

import pytest
import pytest_asyncio

from idu_api.urban_api.schemas import TargetCityTypePost, TerritoryPatch, TerritoryPost, TerritoryTypePost
from idu_api.urban_api.schemas.geometries import Geometry, Point

__all__ = [
    "city",
    "country",
    "district",
    "municipality",
    "region",
    "target_city_type",
    "target_city_type_post_req",
    "territory_type",
    "territory_type_post_req",
    "territory_patch_req",
    "territory_post_req",
]

####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest_asyncio.fixture(scope="function")
async def territory_type(client) -> dict[str, Any]:
    """Returns created territory type."""
    territory_type_post_req = TerritoryTypePost(name="Test Territory Type Name")

    response = await client.post("/api/v1/territory_types", json=territory_type_post_req.model_dump())

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def target_city_type(client) -> dict[str, Any]:
    """Returns created target city type."""
    target_city_type_post_req = TargetCityTypePost(name="Test Target City Type Name", description="Test Description")

    response = await client.post("/api/v1/target_city_types", json=target_city_type_post_req.model_dump())

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def country(client, territory_type) -> dict[str, Any]:
    """Returns created territory `country`."""

    return await create_territory(client, "country", None, False, territory_type["territory_type_id"])


@pytest_asyncio.fixture(scope="function")
async def region(client, territory_type, country) -> dict[str, Any]:
    """Returns created territory `region`."""

    return await create_territory(client, "region", country["territory_id"], False, territory_type["territory_type_id"])


@pytest_asyncio.fixture(scope="function")
async def district(client, territory_type, region) -> dict[str, Any]:
    """Returns created territory `district`."""

    return await create_territory(
        client, "district", region["territory_id"], False, territory_type["territory_type_id"]
    )


@pytest_asyncio.fixture(scope="function")
async def municipality(client, territory_type, district) -> dict[str, Any]:
    """Returns created territory `municipality`."""

    return await create_territory(
        client, "municipality", district["territory_id"], False, territory_type["territory_type_id"]
    )


@pytest_asyncio.fixture(scope="function")
async def city(client, territory_type, municipality) -> dict[str, Any]:
    """Returns created territory `city`."""

    return await create_territory(
        client, "city", municipality["territory_id"], True, territory_type["territory_type_id"]
    )


####################################################################################
#                                 Models                                           #
####################################################################################


@pytest.fixture
def territory_type_post_req() -> TerritoryTypePost:
    """POST request template for territories types data."""

    return TerritoryTypePost(name="Test Territory Type Name")


@pytest.fixture
def target_city_type_post_req() -> TargetCityTypePost:
    """POST request template for target city types data."""

    return TargetCityTypePost(name="Test Target City Type Name", description="Test Description")


@pytest.fixture
def territory_post_req() -> TerritoryPost:
    """POST request template for territories data."""

    return TerritoryPost(
        name="Test Territory Name",
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
        territory_type_id=1,
        parent_id=1,
        properties={},
        admin_center_id=1,
        target_city_type_id=1,
        okato_code="1",
        oktmo_code="1",
        is_city=False,
    )


@pytest.fixture
def territory_patch_req() -> TerritoryPatch:
    """PATCH request template for territories data."""

    return TerritoryPatch(
        name="New Patched Territory Name",
        parent_id=1,
        territory_type_id=1,
        admin_center_id=1,
        target_city_type_id=1,
    )


####################################################################################
#                                 Helpers                                          #
####################################################################################


async def create_territory(
    client,
    name: str,
    parent_id: int | None,
    is_city: bool,
    territory_type_id: int,
) -> dict[str, Any]:
    """Creates new territory."""

    territory = {
        "name": name,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        },
        "territory_type_id": territory_type_id,
        "parent_id": parent_id,
        "is_city": is_city,
    }

    response = await client.post("/api/v1/territory", json=territory)

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()
