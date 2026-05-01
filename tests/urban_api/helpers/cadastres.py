"""All fixtures for project cadastres tests are defined here."""

from typing import Any

import pytest
import pytest_asyncio

from idu_api.urban_api.schemas import ProjectCadastrePut
from idu_api.urban_api.schemas.geometries import Geometry

####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest_asyncio.fixture(scope="function")
async def project_cadastre(client, project, superuser_token) -> dict[str, Any]:
    """Returns created project cadastre."""
    cadastre = ProjectCadastrePut(
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
    )
    project_id = project["project_id"]
    headers = {"Authorization": f"Bearer {superuser_token}"}

    response = await client.put(
        f"/api/v1/projects/{project_id}/cadastres",
        json=[cadastre.model_dump()],
        headers=headers,
    )
    result = await client.get(f"/api/v1/projects/{project_id}/cadastres", headers=headers)

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    return result.json()["features"][0]["properties"]


####################################################################################
#                                 Models                                           #
####################################################################################


@pytest.fixture
def project_cadastre_put_req() -> ProjectCadastrePut:
    """PUT request template for project cadastre data."""

    return ProjectCadastrePut(
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
    )
