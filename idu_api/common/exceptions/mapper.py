"""Mapper from exceptions to HTTP responses is defined here"""

from typing import Callable, Type

from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ExceptionMapper:
    """Maps exceptions to `JSONResponse` for FastAPI error handling."""

    def __init__(self, debug: bool = False):
        self._known_exceptions: dict[Type, Callable[[Exception], JSONResponse]] = {}
        self._debug = debug

    def register_simple(self, exception_type: Type, status_code: int, detail: str) -> None:
        """Register simple response handler with setting status_code and detail."""
        self._known_exceptions[exception_type] = lambda exc: JSONResponse(
            {
                "error_type": self._format_exception_type(exception_type),
                "error": str(exc),
                "detail": detail,
            },
            status_code=status_code,
        )

    def register_func(self, exception_type: Type, func: Callable[[Exception], JSONResponse]) -> None:
        """Register complex response handler by passing function."""
        self._known_exceptions[exception_type] = func

    def get_status_code(self, exc: Exception) -> int:
        """Get status code of preparing response."""
        exc = self._get_real_exception(exc)
        if isinstance(exc, HTTPException):
            return exc.status_code
        if type(exc) in self._known_exceptions:
            return self._known_exceptions[type(exc)](exc).status_code
        return 500

    def is_known(self, exc: Exception) -> bool:
        """Return True if mapper can handle this exception not as regular http-500."""
        # exc = self._get_real_exception(exc)
        return type(exc) in self._known_exceptions or isinstance(exc, HTTPException)

    def apply(self, exc: Exception) -> JSONResponse:
        """Get a JOSN response with information about the given exception. If no mapping is found,
        regular http-500 view is returned.
        """
        exc = self._get_real_exception(exc)
        if (res := self.apply_if_known(exc)) is not None:
            return res
        return JSONResponse(
            {
                "error_type": self._format_exception_type(type(exc)),
                "error": str(exc),
                "detail": "unhandled exception",
            },
            status_code=500,
        )

    def apply_if_known(self, exc: Exception) -> JSONResponse | None:
        """Get a JOSN response with information about the given exception.
        If no mapping is found, `None` is returned.
        """
        exc = self._get_real_exception(exc)
        if isinstance(exc, HTTPException):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if (t := type(exc)) in self._known_exceptions:
            return self._known_exceptions[t](exc)
        return None

    @staticmethod
    def _get_real_exception(exc: Exception) -> Exception:
        while isinstance(exc, BaseExceptionGroup):
            exc = exc.args[0]
        return exc

    def _format_exception_type(self, exception_type: Type) -> str:
        if self._debug:
            return f"{exception_type.__module__}.{exception_type.__qualname__}"
        return exception_type.__qualname__
