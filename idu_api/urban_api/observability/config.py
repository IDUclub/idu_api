"""Observability config is defined here."""

from dataclasses import dataclass, field
from typing import Literal

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

    root_logger_level: LoggingLevel = "INFO"
    stderr_level: LoggingLevel | None = None
    exporter: ExporterConfig | None = None
    files: list[FileLogger] = field(default_factory=list)

    def __post_init__(self):
        if len(self.files) > 0 and isinstance(self.files[0], dict):
            self.files = [FileLogger(**f) for f in self.files]


@dataclass
class PrometheusConfig:
    """Config for Prometheus metrics pull-exporter."""

    host: str
    port: int


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
