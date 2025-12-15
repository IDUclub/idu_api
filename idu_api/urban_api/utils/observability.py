"""Observability helper functions are defined here."""

import logging
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.types import Attributes

LoggingLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class ExporterConfig:
    """OpenTelemetry logs exporter config."""

    endpoint: str
    level: LoggingLevel = "INFO"
    tls_insecure: bool = False


@dataclass
class FileLogger:
    """File sink logger config."""

    filename: str
    level: LoggingLevel


@dataclass
class LoggingConfig:
    """Logger configuration."""

    stderr_level: LoggingLevel | None
    exporter: ExporterConfig | None = None
    root_logger_level: LoggingLevel = "INFO"
    files: list[FileLogger] = field(default_factory=list)

    def __post_init__(self):
        if len(self.files) > 0 and isinstance(self.files[0], dict):
            self.files = [FileLogger(**f) for f in self.files]


@dataclass
class PrometheusConfig:
    """Config for Prometheus metrics pull-exporter."""

    host: str
    port: int
    urls_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class JaegerConfig:
    """Config for Jaeger (OpenTelemetry) traces push-exporter."""

    endpoint: str


@dataclass
class ObservabilityConfig:
    """Full observability config for logs, metrics and traces."""

    logging: LoggingConfig
    prometheus: PrometheusConfig | None = None
    jaeger: JaegerConfig | None = None


def configure_logging(
    config: LoggingConfig,
    tracing_enabled: bool,
) -> structlog.stdlib.BoundLogger:
    files = {logger_config.filename: logger_config.level for logger_config in config.files}

    level_name_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    if tracing_enabled:

        def add_open_telemetry_spans(_, __, event_dict: dict):
            span = trace.get_current_span()
            if not span or not span.is_recording():
                return event_dict

            ctx = span.get_span_context()

            event_dict["span_id"] = format(ctx.span_id, "016x")
            event_dict["trace_id"] = format(ctx.trace_id, "032x")

            return event_dict

        processors.insert(len(processors) - 1, add_open_telemetry_spans)

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(config.root_logger_level)

    if config.stderr_level is not None:

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(processor=structlog.dev.ConsoleRenderer(colors=True))
        )
        stderr_handler.setLevel(level_name_mapping[config.stderr_level])
        root_logger.addHandler(stderr_handler)

    for filename, level in files.items():
        try:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Cannot create directory for log file {filename}, application will most likely crash. {exc!r}")
        file_handler = logging.FileHandler(filename=filename, encoding="utf-8")
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(processor=structlog.processors.JSONRenderer()))
        file_handler.setLevel(level_name_mapping[level])
        root_logger.addHandler(file_handler)

    if config.exporter is not None:
        logger_provider = LoggerProvider(
            resource=Resource.create(
                {
                    "service.name": "urban_api",
                    "service.instance.id": platform.node(),
                }
            ),
        )
        set_logger_provider(logger_provider)

        otlp_exporter = OTLPLogExporter(endpoint=config.exporter.endpoint, insecure=config.exporter.tls_insecure)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

        exporter_handler = AttrFilteredLoggingHandler(
            level=config.exporter.level,
            logger_provider=logger_provider,
        )
        exporter_handler.setLevel(level_name_mapping[config.exporter.level])
        root_logger.addHandler(exporter_handler)

    logger: structlog.stdlib.BoundLogger = structlog.get_logger("urban_api")
    logger.setLevel(level_name_mapping[config.root_logger_level])

    return logger


class URLsMapper:
    """Helper to change URL from given regex pattern to the given static value.

    For example, with map {"/api/debug/.*": "/api/debug/*"} all requests with URL starting with "/api/debug/"
    will be placed in path "/api/debug/*" in metrics.
    """

    def __init__(self, urls_map: dict[str, str]):
        self._map: dict[re.Pattern, str] = {}

        for pattern, value in urls_map.items():
            self.add(pattern, value)

    def add(self, pattern: str, mapped_to: str) -> None:
        """Add entry to the map. If pattern compilation is failed, ValueError is raised."""
        regexp = re.compile(pattern)
        self._map[regexp] = mapped_to

    def map(self, url: str) -> str:
        """Check every map entry with `re.match` and return matched value. If not found, return original string."""
        for regexp, mapped_to in self._map.items():
            if regexp.match(url) is not None:
                return mapped_to
        return url


def get_span_headers() -> dict[str, str]:
    ctx = trace.get_current_span().get_span_context()
    return {
        "X-Span-Id": str(ctx.span_id),
        "X-Trace-Id": str(ctx.trace_id),
    }


class AttrFilteredLoggingHandler(LoggingHandler):
    DROP_ATTRIBUTES = ["_logger"]

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        attributes = LoggingHandler._get_attributes(record)
        for attr in AttrFilteredLoggingHandler.DROP_ATTRIBUTES:
            if attr in attributes:
                del attributes[attr]
        return attributes
