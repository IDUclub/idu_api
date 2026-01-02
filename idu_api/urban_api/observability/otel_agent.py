"""Open Telemetry agent initialization is defined here"""

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from idu_api.urban_api.observability.config import JaegerConfig, PrometheusConfig
from idu_api.urban_api.version import VERSION as APP_VERSION

from .metrics_server import PrometheusServer


class OpenTelemetryAgent:  # pylint: disable=too-few-public-methods
    def __init__(self, prometheus_config: PrometheusConfig | None, jaeger_config: JaegerConfig | None):
        self._resource = Resource.create(
            attributes={
                SERVICE_NAME: "urban_api",
                SERVICE_VERSION: APP_VERSION,
            }
        )
        self._prometheus: PrometheusServer | None = None
        self._span_exporter: OTLPSpanExporter | None = None

        if prometheus_config is not None:
            self._prometheus = PrometheusServer(port=prometheus_config.port, host=prometheus_config.host)

            reader = PrometheusMetricReader()
            provider = MeterProvider(resource=self._resource, metric_readers=[reader])
            metrics.set_meter_provider(provider)

        if jaeger_config is not None:
            self._span_exporter = OTLPSpanExporter(endpoint=jaeger_config.endpoint)

            tracer_provider = TracerProvider(resource=self._resource)
            processor = BatchSpanProcessor(span_exporter=self._span_exporter)
            tracer_provider.add_span_processor(processor)
            trace.set_tracer_provider(tracer_provider)

    def shutdown(self) -> None:
        """Stop metrics and tracing services if they were started."""
        if self._prometheus is not None:
            self._prometheus.shutdown()
