"""Application metrics are defined here."""

import threading
import time
from dataclasses import dataclass
from typing import Callable

import psutil
from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import Counter, Histogram, UpDownCounter

from idu_api.urban_api.version import VERSION


@dataclass
class HTTPMetrics:
    request_processing_duration: Histogram
    """Processing time histogram in seconds by `["method", "path"]`."""
    requests_started: Counter
    """Total started requests counter by `["method", "path"]`."""
    requests_finished: Counter
    """Total finished requests counter by `["method", "path", "status_code", "handler_found"]`."""
    errors: Counter
    """Total errors (exceptions) counter by `["method", "path", "error_type", "status_code"]`."""
    inflight_requests: UpDownCounter
    """Current number of requests handled simultaniously."""


@dataclass
class Metrics:
    http: HTTPMetrics


def setup_metrics() -> Metrics:
    meter = metrics.get_meter("urban_api")

    _setup_callback_metrics(meter)

    return Metrics(
        http=HTTPMetrics(
            request_processing_duration=meter.create_histogram(
                "request_processing_duration",
                "sec",
                "Request processing duration time in seconds",
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
            requests_started=meter.create_counter("requests_started_total", "1", "Total number of started requests"),
            requests_finished=meter.create_counter("request_finished_total", "1", "Total number of finished requests"),
            errors=meter.create_counter("request_errors_total", "1", "Total number of errors (exceptions) in requests"),
            inflight_requests=meter.create_up_down_counter(
                "inflight_requests", "1", "Current number of requests handled simultaniously"
            ),
        )
    )


def _setup_callback_metrics(meter: metrics.Meter) -> None:
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
    def system_metrics_callback(options: CallbackOptions):  # pylint: disable=unused-argument
        """Callback function to collect system metrics"""

        # Process CPU time, a bit more information than `process_cpu_seconds_total`
        cpu_times = psutil.Process().cpu_times()
        yield Observation(cpu_times.user, {"resource": "cpu", "mode": "user"})
        yield Observation(cpu_times.system, {"resource": "cpu", "mode": "system"})

    return system_metrics_callback


def _get_application_metrics_callback() -> Callable[[CallbackOptions], None]:
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
