"""Authentication information dependency is defined here."""

from collections.abc import Callable

from fastmcp.dependencies import Depends
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_http_headers, get_http_request
from fastmcp.server.http import StarletteWithLifespan
from starlette.requests import Request
from tenacity import RetryError

from idu_api.urban_api.dependencies import logger_dep
from idu_api.urban_api.dto.users.users import UserDTO
from idu_api.urban_api.exceptions.logic.users import AuthorizationError, NotAuthorizedError
from idu_api.urban_api.exceptions.services.auth import AuthTokenExpiredError, InvalidTokenSignature, JWTDecodeError
from idu_api.urban_api.utils.auth_client import AuthenticationClient


class AnyTokenVerifier(TokenVerifier):

    async def verify_token(self, token: str) -> AccessToken:
        if not token:
            raise AuthorizationError("Bearer token is required")

        return AccessToken(token=token, client_id="unknown", scopes=[], claims={})


def init_dispencer(app: StarletteWithLifespan, auth_client: AuthenticationClient) -> None:
    """Initialize Authentication information dispencer at app's state."""
    if hasattr(app.state, "auth_dep"):
        if not isinstance(app.state.auth_dep, AuthenticationClient):
            raise ValueError(
                f"auth_dep attribute of app's state is already set with other value ({app.state.auth_dep})"
            )
        return

    app.state.auth_dep = auth_client


async def _from_request(request: Request, required: bool = True) -> UserDTO | None:
    """Extract user from request (with caching in `request.state`)."""
    if hasattr(request.state, "auth_user_dep"):
        user = request.state.auth_user_dep
    else:
        auth_client: AuthenticationClient = request.app.state.auth_dep
        headers = get_http_headers(include_all=True)
        try:
            authorization = headers.get("authorization", "")
            if authorization.startswith("Bearer "):
                token = authorization.split(" ", 1)[1]
                user = await auth_client.get_user_from_token(token)
            else:
                user = None

            request.state.auth_user_dep = user

        except AuthTokenExpiredError:
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Токен истёк."

        except InvalidTokenSignature:
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Неверная подпись токена."

        except JWTDecodeError:
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Ошибка декодирования JWT."

        except RetryError:
            logger = logger_dep.from_request(request)
            await logger.aerror("authentication service unavailable")
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Сервер аутентификации недоступен."

        except Exception:  # pylint: disable=broad-except
            logger = logger_dep.from_request(request)
            await logger.aexception("unexpected authentication error")
            request.state.auth_user_dep = None
            request.state.auth_user_missing_reason = "Ошибка обработки токена."

        user = request.state.auth_user_dep

    if required and user is None:
        if hasattr(request.state, "auth_user_missing_reason"):
            raise AuthorizationError(request.state.auth_user_missing_reason)
        raise NotAuthorizedError()

    return user


async def from_request_optional(request: Request | None = None) -> UserDTO | None:
    """Optional user."""
    if request is None:
        request = get_http_request()
    return await _from_request(request, required=False)


async def from_request(request: Request | None = None) -> UserDTO:
    """Required user (401 if there is no user)."""
    if request is None:
        request = get_http_request()
    return await _from_request(request, required=True)


def require_roles(required_roles: list[str]) -> Callable:
    """
    Dependency for role-based access control.

    Usage example:
        user = Depends(require_roles(["ADMIN"]))
    """

    async def checker(user: UserDTO = Depends(from_request)) -> UserDTO:
        user_roles = getattr(user, "roles", [])

        if not any(role in user_roles for role in required_roles):
            raise AuthorizationError("Недостаточно прав")

        return user

    return checker
