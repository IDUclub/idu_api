"""Exception handling middleware is defined here."""

import asyncio
from typing import Any

from fastmcp.exceptions import NotFoundError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from mcp import ErrorData, McpError
from opentelemetry import trace
from opentelemetry.sdk.metrics import Counter

from idu_api.urban_mcp.dependencies import logger_dep
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper


class ExceptionHandlerMiddleware(Middleware):
    """Handle exceptions, so they become MCP error code 32603 - Internal Error.

    If debug is activated in app configuration, then stack trace is returned, otherwise only a generic error message.
    Message is sent to logger error stream anyway.
    """

    def __init__(
        self,
        debug: bool,
        exception_mapper: ExceptionMapper,
        errors_metric: Counter,
    ):
        super().__init__()
        self._debug = debug
        self._exception_mapper = exception_mapper
        self._metric = errors_metric

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        try:
            return await call_next(context)
        except Exception as exc:  # pylint: disable=broad-except
            return await self._handle_exception(exc, context)

    async def _handle_exception(self, exc: Exception, context: MiddlewareContext):
        unwrapped_exc = _unwrap(exc)
        is_known = isinstance(unwrapped_exc, McpError) or self._exception_mapper.is_known(unwrapped_exc)
        mapped = self._map_exception(unwrapped_exc)
        error_code = mapped.error.code
        error_type = type(unwrapped_exc).__qualname__

        request = get_http_request()
        attrs = {"method": context.method or "unknown"}
        if context.method == "tools/call" and hasattr(context.message, "name"):
            attrs["tool"] = context.message.name
        if context.method == "resources/read" and hasattr(context.message, "uri"):
            attrs["uri"] = context.message.uri

        self._metric.add(
            1,
            {
                **attrs,
                "error_type": error_type,
                "error_code": error_code,
            },
        )

        logger = logger_dep.from_request(request)
        if is_known:
            log_func = logger.aerror
        else:
            log_func = logger.aexception
        await log_func("failed to handle request", error_type=error_type, error_code=error_code)

        span = trace.get_current_span()
        span.record_exception(mapped, {"is_known": is_known})
        span.set_status(trace.StatusCode.ERROR)
        span.set_attributes(
            {
                "exception.type": error_type,
                "exception.message": repr(mapped),
                **attrs,
                "error_code": error_code,
            }
        )

        raise mapped from exc

    def _map_exception(self, exc: Exception) -> McpError:
        """Convert exception to MCP-compliant error."""
        if isinstance(exc, McpError):
            return exc

        mapped = self._exception_mapper.apply_if_known(exc)
        if mapped is not None:
            return mapped

        cause = exc.__cause__ or exc

        if isinstance(cause, (ValueError, TypeError)):
            code = -32602
            message = f"Invalid params: {cause}"

        elif isinstance(cause, (KeyError, FileNotFoundError, NotFoundError)):
            code = -32001
            message = f"Not found: {cause}"

        elif isinstance(cause, PermissionError):
            code = -32000
            message = f"Permission denied: {cause}"

        elif isinstance(cause, (TimeoutError, asyncio.TimeoutError)):
            code = -32000
            message = f"Timeout: {cause}"

        else:
            code = -32603
            message = "Internal server error"

            if self._debug:
                message = f"{type(cause).__name__}: {cause}"

        return McpError(
            ErrorData(
                code=code,
                message=message,
            )
        )


def _unwrap(exc: Exception) -> Exception:
    while True:
        if isinstance(exc, McpError):
            return exc

        if hasattr(exc, "__cause__") and exc.__cause__:
            exc = exc.__cause__
            continue

        if isinstance(exc, BaseExceptionGroup) and exc.exceptions:
            exc = exc.exceptions[0]
            continue

        return exc
