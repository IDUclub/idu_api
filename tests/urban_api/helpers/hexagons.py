"""All fixtures for hexagons tests are defined here."""

from typing import Any

import pytest
import pytest_asyncio

from idu_api.urban_api.schemas import HexagonPost
from idu_api.urban_api.schemas.geometries import Geometry

__all__ = ["hexagon", "hexagon_post_req"]

####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest_asyncio.fixture(scope="function")
async def hexagon(client, region) -> dict[str, Any]:
    """Returns created hexagon."""
    hexagon_post_req = HexagonPost(
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
        properties={},
    )

    response = await client.post(
        f"/v1territory/{region['territory_id']}/hexagons", json=[hexagon_post_req.model_dump()]
    )

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return response.json()[0]


####################################################################################
#                                 Models                                           #
####################################################################################


@pytest.fixture
def hexagon_post_req() -> HexagonPost:
    """POST request template for hexagons data."""

    return HexagonPost(
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
        properties={},
    )
