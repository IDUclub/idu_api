"""Metrics dependency functions are defined here."""

from fastapi import FastAPI, Request

from idu_api.urban_api.observability.metrics import Metrics


def init_dispencer(app: FastAPI, connection_manager: Metrics) -> None:
    """Initialize Metrics dispencer at app's state."""
    if hasattr(app.state, "metrics_dep"):
        if not isinstance(app.state.metrics_dep, Metrics):
            raise ValueError(
                f"metrics_dep attribute of app's state is already set with other value ({app.state.metrics_dep})"
            )
        return

    app.state.metrics_dep = connection_manager


def obtain(app_or_request: FastAPI | Request) -> Metrics:
    """Get a Metrics from request's app state."""
    if isinstance(app_or_request, Request):
        app_or_request = app_or_request.app
    if not hasattr(app_or_request.state, "metrics_dep"):
        raise ValueError("Metrics dispencer was not initialized at app preparation")
    return app_or_request.state.metrics_dep
