"""Mapper from exceptions to HTTP responses is defined here"""

from collections.abc import Callable
from typing import Any

from mcp import ErrorData, McpError


class ExceptionMapper:
    """Maps exceptions to McpError for FastMCP error handling."""

    def __init__(self, debug: bool = False):
        self._known_exceptions: dict[type, Callable[[Exception], McpError]] = {}
        self._debug = debug

    def register_simple(self, exception_type: type, code: int, message: str) -> None:
        """Register simple mapping with MCP error code and message."""

        def _handler(exc: Exception) -> McpError:
            return McpError(
                ErrorData(
                    code=code,
                    message=message,
                    data=self._build_data(exc),
                )
            )

        self._known_exceptions[exception_type] = _handler

    def register_func(self, exception_type: type, func: Callable[[Exception], McpError]) -> None:
        """Register custom mapping function."""
        self._known_exceptions[exception_type] = func

    def is_known(self, exc: Exception) -> bool:
        """Return True if mapper can handle this exception not as regular http-500."""
        exc = self._get_real_exception(exc)
        return isinstance(exc, McpError) or type(exc) in self._known_exceptions

    def apply(self, exc: Exception) -> McpError:
        """Convert exception to McpError (always returns something)."""
        exc = self._get_real_exception(exc)

        if isinstance(exc, McpError):
            return exc

        if (mapped := self.apply_if_known(exc)) is not None:
            return mapped

        # fallback → internal error
        return McpError(
            ErrorData(
                code=-32603,  # Internal error
                message="Internal error",
                data=self._build_data(exc) if self._debug else None,
            )
        )

    def apply_if_known(self, exc: Exception) -> McpError | None:
        """Apply mapping only if known."""
        exc = self._get_real_exception(exc)

        if isinstance(exc, McpError):
            return exc

        if (t := type(exc)) in self._known_exceptions:
            return self._known_exceptions[t](exc)

        return None

    @staticmethod
    def _get_real_exception(exc: Exception) -> Exception:
        """Unwrap nested BaseExceptionGroup to get the original exception."""
        while isinstance(exc, BaseExceptionGroup):
            exc = exc.args[0]
        return exc

    def _build_data(self, exc: Exception) -> dict[str, Any]:
        """Build MCP error data payload."""
        data = {
            "error_type": self._format_exception_type(type(exc)),
            "error": str(exc),
        }

        if self._debug:
            data["repr"] = repr(exc)

        return data

    def _format_exception_type(self, exception_type: type) -> str:
        """Return exception type name, optionally including module in debug mode."""
        if self._debug:
            return f"{exception_type.__module__}.{exception_type.__qualname__}"
        return exception_type.__qualname__
