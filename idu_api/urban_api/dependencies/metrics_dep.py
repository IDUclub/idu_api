"""Metrics dependency functions are defined here."""

from fastapi import FastAPI, Request

from idu_api.urban_api.observability.metrics import Metrics


def init_dispencer(app: FastAPI, metrics: Metrics) -> None:
    """Initialize Metrics dispencer at app's state."""
    if hasattr(app.state, "metrics_dep"):
        if not isinstance(app.state.metrics_dep, Metrics):
            raise ValueError(
                f"metrics_dep attribute of app's state is already set with other value ({app.state.metrics_dep})"
            )
        return

    app.state.metrics_dep = metrics


def from_app(app: FastAPI) -> Metrics:
    """Get a Metrics from app state."""
    if not hasattr(app.state, "metrics_dep"):
        raise ValueError("Metrics dispencer was not initialized at app preparation")
    return app.state.metrics_dep


async def from_request(request: Request) -> Metrics:
    """Get a Metrics from request's app state."""
    return from_app(request.app)
