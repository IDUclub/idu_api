"""Console and module entrypoints for the Urban MCP server."""

import os
import tempfile
import typing as tp
from pathlib import Path

import click
import uvicorn

from idu_api.urban_api.utils.dotenv import try_load_envfile

from .config import UrbanMCPConfig


@click.command("Run urban MCP server")
@click.option(
    "--port",
    "-p",
    envvar="PORT",
    type=int,
    show_envvar=True,
    help="Server port number",
)
@click.option(
    "--host",
    envvar="HOST",
    show_envvar=True,
    help="Server HOST address",
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Enable debug mode",
)
@click.option(
    "--config_path",
    envvar="MCP_CONFIG_PATH",
    default="config.yaml",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    show_default=True,
    show_envvar=True,
    help="Path to YAML configuration file",
)
def cli(
    port: int | None,
    host: str | None,
    debug: bool,
    config_path: str,
):
    """Urban MCP backend service entrypoint."""

    print(
        "This is a simple method to run the MCP server. "
        "You might want to use 'uvicorn idu_api.urban_mcp.fastmcp_init:app' instead."
    )

    config = UrbanMCPConfig.load(config_path)

    # --- overrides ---
    if host is not None and host != config.app.uvicorn.host:
        print(f"Overwriting config host with '{host}'")
        config.app.uvicorn.host = host

    if port is not None and port != config.app.uvicorn.port:
        print(f"Overwriting config port with '{port}'")
        config.app.uvicorn.port = port

    if debug:
        print("Overwriting debug with 'True'")
        config.app.debug = True

    with tempfile.TemporaryDirectory(prefix="urban-mcp-") as temp_dir:
        temp_yaml_config_path = Path(temp_dir) / "config.yaml"
        temp_envfile_path = Path(temp_dir) / ".env"
        config.dump(temp_yaml_config_path)
        temp_envfile_path.write_text(f"MCP_CONFIG_PATH={temp_yaml_config_path.as_posix()}\n", encoding="utf-8")

        previous_config_path = os.environ.get("MCP_CONFIG_PATH")
        os.environ["MCP_CONFIG_PATH"] = str(temp_yaml_config_path)
        try:
            uvicorn_config = {
                "host": config.app.uvicorn.host,
                "port": config.app.uvicorn.port,
                "log_level": config.observability.logging.root_logger_level.lower(),
                "env_file": str(temp_envfile_path),
                "access_log": False,
            }

            if config.app.uvicorn.reload:
                try:
                    _run_uvicorn(uvicorn_config | {"reload": True})
                except Exception:  # pylint: disable=broad-exception-caught
                    print("Retrying with reload disabled")
                    _run_uvicorn(uvicorn_config)
            else:
                _run_uvicorn(uvicorn_config)
        finally:
            if previous_config_path is None:
                os.environ.pop("MCP_CONFIG_PATH", None)
            else:
                os.environ["MCP_CONFIG_PATH"] = previous_config_path


def _run_uvicorn(configuration: dict[str, tp.Any]) -> None:
    """Run the ASGI application, returning when the server stops."""
    uvicorn.run(
        "idu_api.urban_mcp.fastmcp_init:app",
        **configuration,
    )


def main() -> None:
    """Load environment defaults before parsing CLI options for either entrypoint."""
    try_load_envfile(os.environ.get("ENVFILE", ".env"))
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
