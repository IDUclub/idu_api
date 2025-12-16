"""Cadastres projects-related endpoints are defined here."""

from fastapi import Depends, Path, Request, Security
from fastapi.security import HTTPBearer
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from pydantic import conlist
from starlette import status

from idu_api.urban_api.dependencies import auth_dep
from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.handlers.v1.projects.routers import projects_router
from idu_api.urban_api.logic.projects import UserProjectService
from idu_api.urban_api.schemas import OkResponse, ProjectCadastreAttributes, ProjectCadastrePut
from idu_api.urban_api.schemas.geojson import GeoJSONResponse


@projects_router.get(
    "/projects/{project_id}/cadastres",
    response_model=GeoJSONResponse[Feature[Geometry, ProjectCadastreAttributes]],
    status_code=status.HTTP_200_OK,
)
async def get_cadastres_by_project_id(
    request: Request,
    project_id: int = Path(..., description="project identifier", gt=0),
    user: UserDTO = Depends(auth_dep.from_request_optional),
) -> GeoJSONResponse[Feature[Geometry, ProjectCadastreAttributes]]:
    """
    ## Get cadastres in GeoJSON format for a given project.

    ### Parameters:
    - **project_id** (int, Path): Unique identifier of the project.

    ### Returns:
    - **GeoJSONResponse[Feature[Geometry, ProjectCadastreAttributes]]**: Project's cadastres in GeoJSON format.

    ### Errors:
    - **403 Forbidden**: If the user does not have access rights.
    - **404 Not Found**: If the project does not exist.

    ### Constraints:
    - The user must be the relevant project owner or the project must be publicly accessible.
    """
    user_project_service: UserProjectService = request.state.user_project_service

    cadastres = await user_project_service.get_cadastres(project_id, user)

    return await GeoJSONResponse.from_list([cadastre.to_geojson_dict() for cadastre in cadastres])


@projects_router.put(
    "/projects/{project_id}/cadastres",
    response_model=OkResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(HTTPBearer())],
)
async def put_project_cadastres(
    request: Request,
    cadastres: conlist(ProjectCadastrePut, min_length=1),
    project_id: int = Path(..., description="project identifier", gt=0),
    user: UserDTO = Depends(auth_dep.from_request),
) -> OkResponse:
    """
    ## Create new cadastres for a given project.

    **WARNING:** This method will delete all cadastres for the specified project before adding new ones.

    ### Parameters:
    - **project_id** (int, Path): Unique identifier of the project.
    - **cadastres** (list[ProjectCadastrePut], Body): List of cadastres to be added.

    ### Returns:
    - **OkResponse**: A confirmation message of the update.

    ### Errors:
    - **403 Forbidden**: If the user does not have access rights.
    - **404 Not Found**: If the project (or related entity) does not exist.

    ### Constraints:
    - The user must be the relevant project owner.
    """
    user_project_service: UserProjectService = request.state.user_project_service

    await user_project_service.put_cadastres(cadastres, project_id, user)

    return OkResponse()


@projects_router.delete(
    "/projects/{project_id}/cadastres",
    response_model=OkResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Security(HTTPBearer())],
)
async def delete_cadastres_by_project_id(
    request: Request,
    project_id: int = Path(..., description="project identifier", gt=0),
    user: UserDTO = Depends(auth_dep.from_request),
) -> OkResponse:
    """
    ## Delete all cadastres associated with a given project.

    ### Parameters:
    - **project_id** (int, Path): Unique identifier of the project.

    ### Returns:
    - **OkResponse**: A confirmation message of the deletion.

    ### Errors:
    - **403 Forbidden**: If the user does not have access rights.
    - **404 Not Found**: If the project does not exist.

    ### Constraints:
    - The user must be the relevant project owner.
    """
    user_project_service: UserProjectService = request.state.user_project_service

    await user_project_service.delete_cadastres(project_id, user)

    return OkResponse()
