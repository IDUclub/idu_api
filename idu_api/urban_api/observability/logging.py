"""Logging-related configuration is located here."""

import json
import logging
import platform
import sys
from pathlib import Path
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
    LogRecordProcessor,
    ReadWriteLogRecord,
)
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.types import Attributes

from .config import LoggingConfig


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
        logger_provider.add_log_record_processor(OtelLogPreparationProcessor())
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


class AttrFilteredLoggingHandler(LoggingHandler):
    DROP_ATTRIBUTES = ["_logger"]

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        attributes = LoggingHandler._get_attributes(record)
        for attr in AttrFilteredLoggingHandler.DROP_ATTRIBUTES:
            if attr in attributes:
                del attributes[attr]
        return attributes


class OtelLogPreparationProcessor(LogRecordProcessor):
    """Processor which moves everything except message from log record body to attributes."""

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:
        if not isinstance(log_record.log_record.body, dict):
            return
        for key in log_record.log_record.body:
            if key == "event":
                continue
            save_key = key
            if key in log_record.log_record.attributes:
                save_key = f"{key}__body"
            log_record.log_record.attributes[save_key] = self._format_value(log_record.log_record.body[key])
        log_record.log_record.body = log_record.log_record.body["event"]

    def _format_value(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def force_flush(self, timeout_millis=30000):
        pass

    def shutdown(self):
        pass
