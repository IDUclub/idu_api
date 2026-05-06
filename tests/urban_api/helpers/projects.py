"""All fixtures for projects tests are defined here."""

import asyncio
import io
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from PIL import Image

from idu_api.urban_api.schemas import ProjectPatch, ProjectPhasesPut, ProjectPost, ProjectTerritoryPost
from idu_api.urban_api.schemas.geometries import Geometry

__all__ = [
    "project",
    "project_image",
    "project_patch_req",
    "project_post_req",
    "project_phases_put_req",
    "regional_project",
]


####################################################################################
#                        Integration tests helpers                                 #
####################################################################################


@pytest_asyncio.fixture(scope="function")
async def regional_project(client, region, superuser_token) -> dict[str, Any]:
    """Returns created regional project."""
    project_post_req = ProjectPost(
        name="Test Project Name",
        territory_id=region["territory_id"],
        description="Test Project Description",
        public=False,
        is_city=False,
        is_regional=True,
        territory=None,
    )
    headers = {"Authorization": f"Bearer {superuser_token}"}

    response = await client.post("/api/v1/projects", json=project_post_req.model_dump(), headers=headers)

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}.\n{response.json()}"
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def project(
    client,
    region,
    superuser_token,
    base_regional_scenario,
    regional_project,
    functional_zone,
    urban_object,
) -> dict[str, Any]:
    """Returns created project."""
    project_post_req = ProjectPost(
        name="Test Project Name",
        territory_id=region["territory_id"],
        description="Test Project Description",
        public=False,
        is_city=False,
        is_regional=False,
        territory=ProjectTerritoryPost(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
            ),
        ),
    )
    headers = {"Authorization": f"Bearer {superuser_token}"}

    await asyncio.sleep(5)
    response = await client.post("/api/v1/projects", json=project_post_req.model_dump(), headers=headers, timeout=10000)

    assert response.status_code == 201, f"Invalid status code was returned: {response.status_code}.\n{response.json()}"
    return response.json()


####################################################################################
#                                 Models                                           #
####################################################################################


@pytest.fixture
def project_post_req() -> ProjectPost:
    """POST request template for user projects data."""

    return ProjectPost(
        name="Test Project Name",
        territory_id=1,
        description="Test Project Description",
        public=True,
        is_city=False,
        territory=ProjectTerritoryPost(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[30.22, 59.86], [30.22, 59.85], [30.25, 59.85], [30.25, 59.86], [30.22, 59.86]]],
            ),
        ),
    )


@pytest.fixture
def project_phases_put_req() -> ProjectPhasesPut:
    """PUT request template for project phases data"""

    return ProjectPhasesPut(
        actual_start_date=date(2024, 1, 1),
        actual_end_date=date(2024, 1, 1),
        planned_end_date=date(2024, 1, 1),
        planned_start_date=date(2024, 1, 1),
        pre_design=1,
        design=1,
        investment=1,
        construction=1,
        operation=1,
        decommission=1,
        properties={},
    )


@pytest.fixture
def project_patch_req() -> ProjectPatch:
    """PATCH request template for user projects data."""

    return ProjectPatch(name="New Patched Project Name")


@pytest.fixture
def project_image() -> bytes:
    """Get simple project image bytes array."""

    img = Image.new("RGB", (60, 30), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")

    return img_byte_arr.getvalue()
