"""structlog BoundLogger dependency functions are defined here."""

from fastapi import FastAPI, Request
from structlog.stdlib import BoundLogger


def init_dispencer(app: FastAPI, logger: BoundLogger) -> None:
    """Initialize BoundLogger dispencer at app's state."""
    if hasattr(app.state, "logger"):
        if not isinstance(app.state.logger_dep, BoundLogger):
            raise ValueError(
                f"logger attribute of app's state is already set with other value ({app.state.logger_dep})"
            )
        return

    app.state.logger_dep = logger


def attach_to_request(request: Request, logger: BoundLogger) -> None:
    """Set logger for a concrete request. If request had already had a logger, replace it."""
    if hasattr(request.state, "logger_dep"):
        if not isinstance(request.state.logger_dep, BoundLogger):
            logger.warning("request.state.logger is already set with other value", value=request.state.logger_dep)
    request.state.logger_dep = logger


def from_app(app: FastAPI) -> BoundLogger:
    """Get a logger from request or app state."""
    if not hasattr(app.state, "logger_dep"):
        raise ValueError("BoundLogger dispencer was not initialized at app preparation")
    return app.state.logger_dep


def from_request(request: Request) -> BoundLogger:
    """Get a logger from request or app state."""
    if hasattr(request.state, "logger_dep"):
        logger = request.state.logger_dep
        if isinstance(logger, BoundLogger):
            return logger
    return from_app(request.app)
