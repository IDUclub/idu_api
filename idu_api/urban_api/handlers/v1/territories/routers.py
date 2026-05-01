"""All FastApi handlers for territories are exported from this module."""

from fastapi import APIRouter

territories_router = APIRouter(tags=["territories"], prefix="/v1")

routers_list = [
    territories_router,
]

__all__ = [
    "routers_list",
]
