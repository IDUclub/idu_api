"""Authentication information dependency is defined here."""

from fastapi import FastAPI, Request
from tenacity import RetryError

from idu_api.urban_api.dependencies import logger_dep
from idu_api.urban_api.dto.users.users import UserDTO
from idu_api.urban_api.exceptions.logic.users import AuthorizationError, NotAuthorizedError
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


async def _from_request(request: Request, required: bool = True) -> UserDTO | None:
    """Get an Authentication information from request's state."""
    if not hasattr(request.state, "auth_user_dep"):
        auth_client: AuthenticationClient = request.app.state.auth_dep
        try:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ", 1)[1]
                request.state.auth_user_dep = await auth_client.get_user_from_token(token)
            else:
                request.state.auth_user_dep = None
        except RetryError:
            logger = await logger_dep.from_request(request)
            await logger.aerror("could not connect to authentication server")
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Сервер аутентификации недоступен."
        except Exception:  # pylint: disable=broad-except
            logger = await logger_dep.from_request(request)
            await logger.aexception("unexpected error in authentication process")
            if not required:
                raise
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Ошибка обработки JWT-токена."
    if required and request.state.auth_user_dep is None:
        if hasattr(request.state, "auth_user_missing_reason"):
            raise AuthorizationError(request.state.auth_user_missing_reason)
        raise NotAuthorizedError()

    return request.state.auth_user_dep


async def from_request_optional(request: Request) -> UserDTO | None:
    return await _from_request(request, required=False)


async def from_request(request: Request) -> UserDTO:
    return await _from_request(request, required=True)
