"""Observability-related utility functions and classes are located here."""

from opentelemetry import trace


def get_tracing_headers() -> dict[str, str]:
    """Extract tracing headers from the current OpenTelemetry span context.

    Returns:
        A dictionary containing span and trace identifiers if tracing is active,
        otherwise an empty dictionary.
    """
    ctx = trace.get_current_span().get_span_context()
    if ctx.trace_id == 0:
        return {}
    return {
        "X-Span-Id": format(ctx.span_id, "016x"),
        "X-Trace-Id": format(ctx.trace_id, "032x"),
    }
