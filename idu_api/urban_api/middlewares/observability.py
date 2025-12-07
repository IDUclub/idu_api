"""Observability middleware is defined here."""

import time
from random import randint

import structlog
from fastapi import FastAPI, HTTPException, Request
from opentelemetry import context as tracing_context
from opentelemetry import trace
from opentelemetry.semconv.attributes import exception_attributes, http_attributes, url_attributes
from opentelemetry.trace import NonRecordingSpan, Span, SpanContext, TraceFlags
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from idu_api.urban_api.dependencies import logger_dep
from idu_api.urban_api.exceptions.mapper import ExceptionMapper
from idu_api.urban_api.observability.metrics import Metrics
from idu_api.urban_api.utils.observability import URLsMapper

_tracer = trace.get_tracer_provider().get_tracer(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware for global observability requests.

    - Generate tracing span and adds response header 'X-Trace-Id' and X-Span-Id'
    - Binds trace_id it to logger passing it in request state (`request.state.logger`)
    - Collects metrics for Prometheus

    In case when jaeger is not enabled, trace_id and span_id are generated randomly.
    """

    def __init__(self, app: FastAPI, exception_mapper: ExceptionMapper, metrics: Metrics, urls_mapper: URLsMapper):
        super().__init__(app)
        self._exception_mapper = exception_mapper
        self._http_metrics = metrics.http
        self._urls_mapper = urls_mapper

    async def dispatch(self, request: Request, call_next):
        logger = logger_dep.from_request(request)
        _try_get_parent_span_id(request)
        with _tracer.start_as_current_span("http-request", record_exception=False) as span:
            trace_id = hex(span.get_span_context().trace_id or randint(1, 1 << 63))[2:]
            span_id = span.get_span_context().span_id or randint(1, 1 << 31)
            if trace_id == 0:
                trace_id = format(randint(1, 1 << 63), "016x")
                span_id = format(randint(1, 1 << 31), "032x")
                logger = logger.bind(trace_id=trace_id, span_id=span_id)
            logger_dep.attach_to_request(request, logger)

            span.set_attributes(
                {
                    http_attributes.HTTP_REQUEST_METHOD: request.method,
                    url_attributes.URL_PATH: request.url.path,
                    url_attributes.URL_QUERY: str(request.query_params),
                    "request_client": request.client.host,
                }
            )

            await logger.ainfo(
                "handling request",
                client=request.client.host,
                path_params=request.path_params,
                method=request.method,
                url=str(request.url),
            )

            path_for_metric = self._urls_mapper.map(request.url.path)
            self._http_metrics.requests_started.add(
                1,
                {
                    "method": request.method,
                    "path": path_for_metric,
                },
            )

            time_begin = time.monotonic()
            try:
                result = await call_next(request)
                duration_seconds = time.monotonic() - time_begin

                result.headers.update({"X-Trace-Id": trace_id, "X-Span-Id": str(span_id)})
                await self._handle_success(
                    request=request,
                    status_code=result.status_code,
                    logger=logger,
                    span=span,
                    path_for_metric=path_for_metric,
                    duration_seconds=duration_seconds,
                    handler_found=True,
                )
                return result
            except HandlerNotFoundError as exc:  # hack to filter requests without handlers
                duration_seconds = time.monotonic() - time_begin
                if isinstance(exc, HandlerNotFoundError):
                    exc = exc.__cause__
                await self._handle_success(
                    request=request,
                    status_code=status.HTTP_404_NOT_FOUND,
                    logger=logger,
                    span=span,
                    path_for_metric=path_for_metric,
                    duration_seconds=duration_seconds,
                    handler_found=False,
                )
                raise ObservableException(trace_id=trace_id, span_id=span_id) from exc
            except Exception as exc:
                duration_seconds = time.monotonic() - time_begin
                await self._handle_exception(
                    request=request,
                    exc=exc,
                    logger=logger,
                    span=span,
                    path_for_metric=path_for_metric,
                    duration_seconds=duration_seconds,
                )
                raise ObservableException(trace_id=trace_id, span_id=span_id) from exc
            finally:
                self._http_metrics.request_processing_duration.record(
                    duration_seconds, {"method": request.method, "path": path_for_metric}
                )

    async def _handle_success(  # pylint: disable=too-many-arguments
        self,
        *,
        request: Request,
        status_code: int,
        logger: structlog.stdlib.BoundLogger,
        span: Span,
        path_for_metric: str,
        duration_seconds: float,
        handler_found: bool,
    ) -> None:
        await logger.ainfo("request handled successfully", time_consumed=round(duration_seconds, 3))
        self._http_metrics.requests_finished.add(
            1,
            {
                "method": request.method,
                "path": path_for_metric,
                "status_code": status_code,
                "handler_found": handler_found,
            },
        )

        span.set_attribute(http_attributes.HTTP_RESPONSE_STATUS_CODE, status_code)
        if not handler_found:
            span.set_attribute("handler_found", False)

    async def _handle_exception(  # pylint: disable=too-many-arguments
        self,
        *,
        request: Request,
        exc: Exception,
        logger: structlog.stdlib.BoundLogger,
        span: Span,
        path_for_metric: str,
        duration_seconds: float,
    ) -> None:

        cause = exc
        status_code = self._exception_mapper.get_status_code(exc)
        if isinstance(exc, HTTPException):
            if exc.__cause__ is not None:
                cause = exc.__cause__
        is_known = self._exception_mapper.is_known(exc)

        self._http_metrics.requests_finished.add(
            1,
            {
                "method": request.method,
                "path": path_for_metric,
                "status_code": status_code,
                "handler_found": True,
            },
        )
        self._http_metrics.errors.add(
            1,
            {
                "method": request.method,
                "path": path_for_metric,
                "error_type": type(cause).__qualname__,
                "status_code": status_code,
            },
        )

        span.record_exception(exc, {"is_known": is_known})
        if is_known:
            log_func = logger.aerror
        else:
            log_func = logger.aexception
        await log_func(
            "failed to handle request", time_consumed=round(duration_seconds, 3), error_type=type(exc).__qualname__
        )

        span.set_attributes(
            {
                exception_attributes.EXCEPTION_TYPE: type(exc).__qualname__,
                exception_attributes.EXCEPTION_MESSAGE: repr(exc),
                http_attributes.HTTP_RESPONSE_STATUS_CODE: status_code,
            }
        )


class ObservableException(RuntimeError):
    """Runtime Error with `trace_id` and `span_id` set. Guranteed to have `.__cause__` as its parent exception."""

    def __init__(self, trace_id: str, span_id: int):
        super().__init__()
        self.trace_id = trace_id
        self.span_id = span_id


class HandlerNotFoundError(Exception):
    """Exception to raise on FastAPI 404 handler (only for situation when no handler was found for request).

    Guranteed to have `.__cause__` as its parent exception.
    """


def _try_get_parent_span_id(request: Request) -> None:
    trace_id_str = request.headers.get("X-Trace-Id")
    span_id_str = request.headers.get("X-Span-Id")

    if trace_id_str is None or span_id_str is None:
        return

    if not trace_id_str.isnumeric() or not span_id_str.isnumeric():
        return

    span_context = SpanContext(
        trace_id=int(trace_id_str), span_id=int(span_id_str), is_remote=True, trace_flags=TraceFlags(0x01)
    )
    ctx = trace.set_span_in_context(NonRecordingSpan(span_context))
    tracing_context.attach(ctx)
