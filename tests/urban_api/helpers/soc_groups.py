"""All fixtures for social groups and values tests are defined here."""

from datetime import date
from typing import Any

import pytest
import pytest_asyncio

from idu_api.urban_api.schemas import (
    SocGroupPost,
    SocServiceTypePost,
    SocValueIndicatorValuePost,
    SocValueIndicatorValuePut,
    SocValuePost,
)

__all__ = [
    "soc_value_indicator_post_req",
    "soc_value_indicator_put_req",
    "social_value_indicator",
    "soc_group_post_req",
    "soc_service_type_post_req",
    "soc_value_post_req",
    "social_group",
    "social_value",
]

####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest_asyncio.fixture(scope="function")
async def social_group(client, service_type) -> dict[str, Any]:
    """Returns created social group."""
    soc_group_post_req = SocGroupPost(name="Test Social Group")
    new_service_type = SocServiceTypePost(service_type_id=service_type["service_type_id"], infrastructure_type="basic")

    response = await client.post("/api/v1/social_groups", json=soc_group_post_req.model_dump())
    soc_group_id = response.json()["soc_group_id"]
    response = await client.post(
        f"/api/v1/social_groups/{soc_group_id}/service_types", json=new_service_type.model_dump()
    )

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def social_value(client, service_type) -> dict[str, Any]:
    """Returns created social value."""
    soc_value_post_req = SocValuePost(
        name="Test Social Value",
        rank=1,
        normative_value=1,
        decree_value=1,
    )

    response = await client.post("/api/v1/social_values", json=soc_value_post_req.model_dump())
    soc_value_id = response.json()["soc_value_id"]
    response = await client.post(
        f"/api/v1/social_values/{soc_value_id}/service_types/{service_type['service_type_id']}"
    )

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def social_value_indicator(client, social_value, region) -> dict[str, Any]:
    """Returns created social value's indicator value."""
    soc_value_indicator_post_req = SocValueIndicatorValuePost(
        soc_value_id=social_value["soc_value_id"],
        territory_id=region["territory_id"],
        year=date.today().year,
        value=0.5,
    )

    response = await client.post(
        f"/api/v1/social_values/indicators",
        json=soc_value_indicator_post_req.model_dump(),
    )

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}.\n{response.json()}"
    return response.json()


####################################################################################
#                                 Models                                           #
####################################################################################


@pytest.fixture
def soc_group_post_req() -> SocGroupPost:
    """POST request template for social group data."""

    return SocGroupPost(name="Test Social Group")


@pytest.fixture
def soc_value_post_req() -> SocValuePost:
    """POST request template for social value data."""

    return SocValuePost(name="Test Social Value", rank=1, normative_value=1, decree_value=1)


@pytest.fixture
def soc_value_indicator_post_req() -> SocValueIndicatorValuePost:
    """POST request template for social value's indicator value data."""

    return SocValueIndicatorValuePost(
        soc_value_id=1,
        territory_id=1,
        year=date.today().year,
        value=0.5,
    )


@pytest.fixture
def soc_value_indicator_put_req() -> SocValueIndicatorValuePut:
    """PUT request template for social value's indicator value data."""

    return SocValueIndicatorValuePut(
        soc_value_id=1,
        territory_id=1,
        year=date.today().year,
        value=0.5,
    )


@pytest.fixture
def soc_service_type_post_req() -> SocServiceTypePost:
    """POST request template for social value's service type data."""

    return SocServiceTypePost(
        service_type_id=1,
        infrastructure_type="basic",
    )
