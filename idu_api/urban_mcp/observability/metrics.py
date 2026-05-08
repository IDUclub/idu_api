"""Application metrics are defined here."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import psutil
from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import Counter, Histogram, UpDownCounter

from idu_api.urban_api.version import VERSION


@dataclass
class MCPMetrics:
    """MCP-related OpenTelemetry metrics."""

    processing_duration: Histogram
    """Processing time histogram by ["method", "tool"]"""

    requests_started: Counter
    """Total started MCP calls"""

    requests_finished: Counter
    """Finished MCP calls by ["method", "tool", "status"]"""

    errors: Counter
    """Errors by ["method", "tool", "error_type"]"""

    inflight_requests: UpDownCounter
    """Current in-flight MCP calls"""


@dataclass
class Metrics:
    mcp: MCPMetrics


def setup_metrics() -> Metrics:
    meter = metrics.get_meter("urban_mcp")

    _setup_callback_metrics(meter)

    return Metrics(
        mcp=MCPMetrics(
            processing_duration=meter.create_histogram(
                "mcp_processing_duration",
                "sec",
                "MCP request processing time",
                explicit_bucket_boundaries_advisory=[
                    0.05,
                    0.2,
                    0.3,
                    0.7,
                    1.0,
                    1.5,
                    2.5,
                    5.0,
                    10.0,
                    20.0,
                    40.0,
                    60.0,
                    120.0,
                    240.0,
                ],
            ),
            requests_started=meter.create_counter(
                "mcp_requests_started_total",
                "1",
                "Total MCP requests started",
            ),
            requests_finished=meter.create_counter(
                "mcp_requests_finished_total",
                "1",
                "Total MCP requests finished",
            ),
            errors=meter.create_counter(
                "mcp_request_errors_total",
                "1",
                "Total MCP errors",
            ),
            inflight_requests=meter.create_up_down_counter(
                "mcp_inflight_requests",
                "1",
                "Current MCP in-flight requests",
            ),
        )
    )


def _setup_callback_metrics(meter: metrics.Meter) -> None:
    """Register observable system and application metrics."""

    # Create observable gauge
    meter.create_observable_gauge(
        name="system_resource_usage",
        description="System resource utilization",
        unit="1",
        callbacks=[_get_system_metrics_callback()],
    )
    meter.create_observable_gauge(
        name="application_metrics",
        description="Application-specific metrics",
        unit="1",
        callbacks=[_get_application_metrics_callback()],
    )


def _get_system_metrics_callback() -> Callable[[CallbackOptions], None]:
    """Create callback for collecting system-level metrics."""

    def system_metrics_callback(options: CallbackOptions):  # pylint: disable=unused-argument
        """Callback function to collect system metrics"""

        # Process CPU time, a bit more information than `process_cpu_seconds_total`
        cpu_times = psutil.Process().cpu_times()
        yield Observation(cpu_times.user, {"resource": "cpu", "mode": "user"})
        yield Observation(cpu_times.system, {"resource": "cpu", "mode": "system"})

    return system_metrics_callback


def _get_application_metrics_callback() -> Callable[[CallbackOptions], None]:
    """Create callback for collecting application-level metrics."""
    startup_time = time.time()

    def application_metrics_callback(options: CallbackOptions):  # pylint: disable=unused-argument
        """Callback function to collect application-specific metrics"""
        # Current timestamp
        yield Observation(startup_time, {"metric": "startup_time", "version": VERSION})
        yield Observation(time.time(), {"metric": "last_update_time", "version": VERSION})

        # Active threads
        active_threads = threading.active_count()
        yield Observation(active_threads, {"metric": "active_threads"})

    return application_metrics_callback
