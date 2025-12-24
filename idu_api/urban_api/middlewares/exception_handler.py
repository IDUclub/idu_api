"""Exception handling middleware is defined here."""

import itertools
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from idu_api.urban_api.exceptions.mapper import ExceptionMapper

from .observability import ObservableException


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Handle exceptions, so they become http response code 500 - Internal Server Error.

    If debug is activated in app configuration, then stack trace is returned, otherwise only a generic error message.
    Message is sent to logger error stream anyway.
    """

    def __init__(
        self,
        app: FastAPI,
        debug: bool,
        exception_mapper: ExceptionMapper,
    ):
        super().__init__(app)
        self._debug = debug
        self._mapper = exception_mapper

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            additional_headers: dict[str, str] | None = None
            if isinstance(exc, ObservableException):
                additional_headers = {
                    "X-Trace-Id": format(exc.trace_id, "032x"),
                    "X-Span-Id": format(exc.span_id, "016x"),
                }
                exc = exc.__cause__
            status_code = 500
            detail = "exception occured"

            if isinstance(exc, HTTPException) and hasattr(exc, "status_code"):
                status_code = exc.status_code  # pylint: disable=no-member
                detail = exc.detail  # pylint: disable=no-member

            if self._debug:
                if (res := self._mapper.apply_if_known(exc)) is not None:
                    response = res
                else:
                    response = JSONResponse(
                        {
                            "code": status_code,
                            "detail": detail,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "path": request.url.path,
                            "query_params": request.url.query,
                            "tracebacks": _get_tracebacks(exc),
                        },
                        status_code=status_code,
                    )
            else:
                response = self._mapper.apply(exc)
            if additional_headers is not None:
                response.headers.update(additional_headers)
            return response


def _get_tracebacks(exc: Exception) -> list[list[str]]:
    tracebacks: list[list[str]] = []
    while exc is not None:
        tracebacks.append(
            list(itertools.chain.from_iterable(map(lambda x: x.split("\n"), traceback.format_tb(exc.__traceback__))))
        )
        tracebacks[-1].append(f"{exc.__class__.__module__}.{exc.__class__.__qualname__}: {exc}")
        exc = exc.__cause__
    return tracebacks
