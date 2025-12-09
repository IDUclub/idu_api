"""Authentication information dependency is defined here."""

from fastapi import FastAPI, Request
from tenacity import RetryError

from idu_api.urban_api.dependencies import logger_dep
from idu_api.urban_api.dto.users.users import UserDTO
from idu_api.urban_api.exceptions.services.external import ExternalServiceUnavailable
from idu_api.urban_api.utils.auth_client import AuthenticationClient


def init_dispencer(app: FastAPI, auth_client: AuthenticationClient) -> None:
    """Initialize Authentication information dispencer at app's state."""
    if hasattr(app.state, "auth_dep"):
        if not isinstance(app.state.auth_dep, AuthenticationClient):
            raise ValueError(
                f"auth_dep attribute of app's state is already set with other value ({app.state.auth_dep})"
            )
        return

    app.state.auth_dep = auth_client


async def from_request(request: Request, optional: bool = False) -> UserDTO | None:
    """Get a Authentication information from request's state."""
    if not hasattr(request.state, "auth_user_dep"):
        auth_client: AuthenticationClient = request.app.state.auth_dep
        try:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ", 1)[1]
                request.state.auth_user_dep = await auth_client.get_user_from_token(token)
            else:
                request.state.auth_user_dep = None
        except RetryError as exc:
            logger = await logger_dep.from_request(request)
            await logger.aerror("could not connect to authentication server")
            if not optional:
                raise ExternalServiceUnavailable("сервер аутентификации") from exc
        except Exception:  # pylint: disable=broad-except
            logger = await logger_dep.from_request(request)
            await logger.aexception("unexpected error in authentication process")
            if not optional:
                raise

    return request.state.auth_user_dep


async def from_request_optional(request: Request) -> UserDTO | None:
    return await from_request(request, optional=True)
