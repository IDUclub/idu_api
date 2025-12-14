"""All fixtures for project cadastres tests are defined here."""

from typing import Any

import httpx
import pytest

from idu_api.urban_api.schemas import ProjectCadastrePut
from idu_api.urban_api.schemas.geometries import Geometry

####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest.fixture(scope="session")
def project_cadastre(urban_api_host, project, superuser_token) -> dict[str, Any]:
    """Returns created project cadastre."""
    cadastre = ProjectCadastrePut(
        geometry=Geometry(
            type="Polygon",
            coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
        ),
    )
    project_id = project["project_id"]
    headers = {"Authorization": f"Bearer {superuser_token}"}

    with httpx.Client(base_url=f"{urban_api_host}/api/v1") as client:
        response = client.put(
            f"/projects/{project_id}/cadastres",
            json=[cadastre.model_dump()],
            headers=headers,
        )
        result = client.get(f"/projects/{project_id}/cadastres", headers=headers)

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}."
    print(result.json())
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
