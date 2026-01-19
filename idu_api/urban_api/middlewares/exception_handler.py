"""Exception handling middleware is defined here."""

import itertools
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.sdk.metrics import Counter
from opentelemetry.semconv.attributes import exception_attributes, http_attributes, url_attributes
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from idu_api.urban_api.dependencies import logger_dep
from idu_api.urban_api.exceptions.mapper import ExceptionMapper
from idu_api.urban_api.observability.utils import URLsMapper


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Handle exceptions, so they become http response code 500 - Internal Server Error.

    If debug is activated in app configuration, then stack trace is returned, otherwise only a generic error message.
    Message is sent to logger error stream anyway.
    """

    def __init__(
        self,
        app: FastAPI,
        *,
        debug: bool,
        exception_mapper: ExceptionMapper,
        urls_mapper: URLsMapper,
        errors_metric: Counter,
    ):
        super().__init__(app)
        self._debug = debug
        self._exception_mapper = exception_mapper
        self._urls_mapper = urls_mapper
        self._metric = errors_metric

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            status_code = 500
            detail = "exception occured"

            if isinstance(exc, HandlerNotFoundError):
                exc = exc.__cause__

            cause = exc
            if isinstance(exc, HTTPException):
                status_code = exc.status_code  # pylint: disable=no-member
                detail = exc.detail  # pylint: disable=no-member
                if exc.__cause__ is not None:
                    cause = exc.__cause__

            self._metric.add(
                1,
                {
                    http_attributes.HTTP_REQUEST_METHOD: request.method,
                    url_attributes.URL_PATH: self._urls_mapper.map(request.method, request.url.path),
                    "error_type": type(cause).__qualname__,
                    http_attributes.HTTP_RESPONSE_STATUS_CODE: status_code,
                },
            )

            span = trace.get_current_span()
            logger = logger_dep.from_request(request)

            is_known = self._exception_mapper.is_known(cause)
            span.record_exception(cause, {"is_known": is_known})
            if is_known:
                log_func = logger.aerror
            else:
                log_func = logger.aexception
            await log_func("failed to handle request", error_type=type(cause).__name__)
            span.set_status(trace.StatusCode.ERROR)
            span.set_attributes(
                {
                    exception_attributes.EXCEPTION_TYPE: type(cause).__name__,
                    exception_attributes.EXCEPTION_MESSAGE: repr(cause),
                    http_attributes.HTTP_RESPONSE_STATUS_CODE: status_code,
                }
            )

            if self._debug:
                if (res := self._exception_mapper.apply_if_known(exc)) is not None:
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
                response = self._exception_mapper.apply(exc)
            return response


class HandlerNotFoundError(Exception):
    """Exception to raise on FastAPI 404 handler (only for situation when no handler was found for request).

    Guranteed to have `.__cause__` as its parent exception.
    """


def _get_tracebacks(exc: Exception) -> list[list[str]]:
    tracebacks: list[list[str]] = []
    while exc is not None:
        tracebacks.append(
            list(itertools.chain.from_iterable(map(lambda x: x.split("\n"), traceback.format_tb(exc.__traceback__))))
        )
        tracebacks[-1].append(f"{exc.__class__.__module__}.{exc.__class__.__qualname__}: {exc}")
        exc = exc.__cause__
    return tracebacks
