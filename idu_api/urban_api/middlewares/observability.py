"""Observability middleware is defined here."""

import time
import uuid

from fastapi import FastAPI, Request
from opentelemetry import context as tracing_context
from opentelemetry import trace
from opentelemetry.semconv.attributes import http_attributes, url_attributes
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
from starlette.middleware.base import BaseHTTPMiddleware

from idu_api.urban_api.dependencies import auth_dep, logger_dep
from idu_api.urban_api.observability.metrics import Metrics
from idu_api.urban_api.observability.utils import URLsMapper, get_tracing_headers

_tracer = trace.get_tracer_provider().get_tracer(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware for global observability requests.

    - Generate tracing span and adds response headers
    'X-Trace-Id', 'X-Span-Id' (if tracing is configured) and 'X-Request-Id'
    - Binds trace_id it to logger passing it in request state (`request.state.logger`)
    - Collects metrics for Prometheus

    """

    def __init__(self, app: FastAPI, metrics: Metrics, urls_mapper: URLsMapper):
        super().__init__(app)
        self._http_metrics = metrics.http
        self._urls_mapper = urls_mapper

    async def dispatch(self, request: Request, call_next):
        logger = logger_dep.from_request(request)
        user = await auth_dep.from_request_optional(request)

        _try_get_parent_span_id(request)
        with _tracer.start_as_current_span("http request") as span:
            request_id = str(uuid.uuid4())
            logger = logger.bind(request_id=request_id)
            logger_dep.attach_to_request(request, logger)

            span.set_attributes(
                {
                    http_attributes.HTTP_REQUEST_METHOD: request.method,
                    url_attributes.URL_PATH: request.url.path,
                    url_attributes.URL_QUERY: str(request.query_params),
                    "request_client": request.client.host,
                    "request_id": request_id,
                    "user": user.id if user is not None else "",
                }
            )

            await logger.ainfo(
                "http begin",
                client=request.client.host,
                path_params=request.path_params,
                method=request.method,
                url=str(request.url),
            )

            path_for_metric = self._urls_mapper.map(request.method, request.url.path)
            self._http_metrics.requests_started.add(1, {"method": request.method, "path": path_for_metric})
            self._http_metrics.inflight_requests.add(1)

            time_begin = time.monotonic()
            result = await call_next(request)
            duration_seconds = time.monotonic() - time_begin

            result.headers.update({"X-Request-Id": request_id} | get_tracing_headers())

            await logger.ainfo("http end", time_consumed=round(duration_seconds, 3), status_code=result.status_code)
            self._http_metrics.requests_finished.add(
                1,
                {
                    http_attributes.HTTP_REQUEST_METHOD: request.method,
                    url_attributes.URL_PATH: path_for_metric,
                    http_attributes.HTTP_RESPONSE_STATUS_CODE: result.status_code,
                },
            )
            self._http_metrics.inflight_requests.add(-1)

            if result.status_code // 100 == 2:
                span.set_status(trace.StatusCode.OK)
            span.set_attribute(http_attributes.HTTP_RESPONSE_STATUS_CODE, result.status_code)
            self._http_metrics.request_processing_duration.record(
                duration_seconds, {"method": request.method, "path": path_for_metric}
            )
            return result


def _try_get_parent_span_id(request: Request) -> None:
    trace_id_str = request.headers.get("X-Trace-Id")
    span_id_str = request.headers.get("X-Span-Id")

    if trace_id_str is None or span_id_str is None:
        return

    if not trace_id_str.isalnum() or not span_id_str.isalnum():
        return

    try:
        span_context = SpanContext(
            trace_id=int(trace_id_str, 16), span_id=int(span_id_str, 16), is_remote=True, trace_flags=TraceFlags(0x01)
        )
    except Exception:  # pylint: disable=broad-except
        return
    ctx = trace.set_span_in_context(NonRecordingSpan(span_context))
    tracing_context.attach(ctx)
