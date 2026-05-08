"""Observability middleware is defined here."""

import time
import uuid
from typing import Any

from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from opentelemetry import context as tracing_context
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
from starlette.requests import Request

from idu_api.urban_mcp.dependencies import auth_dep, logger_dep
from idu_api.urban_mcp.observability.metrics import Metrics

_tracer = trace.get_tracer_provider().get_tracer(__name__)


class ObservabilityMiddleware(Middleware):
    """Middleware for global observability requests.

    - Generate tracing span and adds response headers
    'X-Trace-Id', 'X-Span-Id' (if tracing is configured) and 'X-Request-Id'
    - Binds trace_id it to logger passing it in request state (`request.state.logger`)
    - Collects metrics for Prometheus

    """

    def __init__(self, metrics: Metrics):
        super().__init__()
        self._mcp_metrics = metrics.mcp

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        request = get_http_request()
        logger = logger_dep.from_request(request)

        user = await auth_dep.from_request_optional(request)

        _try_get_parent_span_id(request)
        with _tracer.start_as_current_span("mcp request") as span:
            request_id = str(uuid.uuid4())
            logger = logger.bind(request_id=request_id)
            logger_dep.attach_to_request(request, logger)

            attrs = {"method": context.method or "unknown"}
            if context.method == "tools/call" and hasattr(context.message, "name"):
                attrs["tool"] = context.message.name
                attrs["args"] = str(context.message.arguments)
            if context.method == "resources/read" and hasattr(context.message, "uri"):
                attrs["uri"] = context.message.uri

            span.set_attributes(
                {
                    **attrs,
                    "request_client": request.client.host,
                    "request_id": request_id,
                    "azp": user.azp if user is not None else "",
                    "user": user.username if user is not None else "",
                }
            )

            await logger.ainfo(
                "mcp begin",
                client=request.client.host,
                azp=user.azp if user is not None else "unknown",
                **attrs,
            )

            self._mcp_metrics.requests_started.add(1, attrs)
            self._mcp_metrics.inflight_requests.add(1)

            time_begin = time.monotonic()
            try:
                result = await call_next(context)
                duration_seconds = time.monotonic() - time_begin

                self._mcp_metrics.processing_duration.record(duration_seconds, attrs)
                self._mcp_metrics.requests_finished.add(1, {**attrs, "status": "ok"})
                self._mcp_metrics.inflight_requests.add(-1)

                span.set_status(trace.StatusCode.OK)

                await logger.ainfo("mcp end", time_consumed=round(duration_seconds, 3), status="ok")

                return result

            except Exception:
                duration_seconds = time.monotonic() - time_begin

                self._mcp_metrics.processing_duration.record(duration_seconds, attrs)
                self._mcp_metrics.requests_finished.add(1, {**attrs, "status": "error"})
                self._mcp_metrics.inflight_requests.add(-1)

                await logger.ainfo("mcp end", time_consumed=round(duration_seconds, 3), status="error")

                raise


def _try_get_parent_span_id(request: Request) -> None:
    """Try to restore tracing context from incoming request headers."""
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
