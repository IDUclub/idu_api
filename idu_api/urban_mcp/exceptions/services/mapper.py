"""Mapper from logic exceptions to MCP error is defined here."""

from mcp import ErrorData, McpError

from idu_api.urban_api.exceptions.services import auth, external
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper


def _get_mcp_error(code: int, message: str) -> McpError:
    """Create MCP error with a standard structure."""
    return McpError(ErrorData(code=code, message=message))


def register_exceptions(mapper: ExceptionMapper) -> None:
    """Register authentication, external service, and storage-related exceptions."""
    mapper.register_simple(auth.AuthTokenExpiredError, -31002, "Срок действия токена истёк.")
    mapper.register_simple(auth.JWTDecodeError, -31002, "Ошибка декодирования JWT.")
    mapper.register_simple(auth.InvalidTokenSignature, -31002, "Недопустимая подпись токена.")

    mapper.register_func(
        external.ExternalServiceResponseError,
        lambda exc: _get_mcp_error(
            code=-32000,
            message=f"Ошибка в ответе внешнего сервиса '{exc.service}': {exc.error}",
        ),
    )
    mapper.register_func(
        external.ExternalServiceUnavailable,
        lambda exc: _get_mcp_error(
            code=-32050,
            message=f"Внешний сервис ({exc.service}) недоступен.",
        ),
    )
