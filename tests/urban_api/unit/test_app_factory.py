"""Tests for the Urban API application factory."""

import os
import subprocess
import sys
from unittest.mock import patch

from idu_api.urban_api.__main__ import _run_uvicorn


def test_fastapi_init_import_does_not_require_runtime_config() -> None:
    """Importing the factory must not load the production config."""
    environment = os.environ.copy()
    environment.pop("CONFIG_PATH", None)

    result = subprocess.run(
        [sys.executable, "-c", "from idu_api.urban_api.fastapi_init import get_app"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@patch("idu_api.urban_api.__main__.uvicorn.run")
def test_uvicorn_starts_the_application_factory(run_mock) -> None:
    """The CLI must ask Uvicorn to construct the application."""
    configuration = {"host": "127.0.0.1", "port": 8000}

    _run_uvicorn(configuration)

    run_mock.assert_called_once_with(
        "idu_api.urban_api.fastapi_init:get_app",
        factory=True,
        **configuration,
    )
