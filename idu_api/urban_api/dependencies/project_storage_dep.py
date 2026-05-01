"""Projects storage manager (with MinIO cient) dependency is defined here."""

from fastapi import FastAPI, Request

from idu_api.urban_api.minio.services import ProjectStorageManager


def init_dispencer(app: FastAPI, project_storage: ProjectStorageManager) -> None:
    """Initialize ProjectStorageManager dispencer at app's state."""
    if hasattr(app.state, "project_storage_dep"):
        if not isinstance(app.state.project_storage_dep, ProjectStorageManager):
            raise ValueError(
                "project_storage_dep attribute of app's state is already"
                f" set with other value ({app.state.project_storage_dep})"
            )
        return

    app.state.project_storage_dep = project_storage


def from_app(app: FastAPI) -> ProjectStorageManager:
    """Get a ProjectStorageManager from app state."""
    if not hasattr(app.state, "project_storage_dep"):
        raise ValueError("ProjectStorageManager dispencer was not initialized at app preparation")
    return app.state.project_storage_dep


async def from_request(request: Request) -> ProjectStorageManager:
    """Get a ProjectStorageManager from request's app state."""
    return from_app(request.app)
