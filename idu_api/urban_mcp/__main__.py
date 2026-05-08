import os
import tempfile
import typing as tp

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
def main(
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

    # --- temp config (как и раньше) ---
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_yaml_config_path = temp_file.name

    config.dump(temp_yaml_config_path)

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_envfile_path = temp_file.name

    with open(temp_envfile_path, "w", encoding="utf-8") as env_file:
        env_file.write(f"CONFIG_PATH={temp_yaml_config_path}\n")

    os.environ["MCP_CONFIG_PATH"] = temp_yaml_config_path

    try:
        uvicorn_config = {
            "host": config.app.uvicorn.host,
            "port": config.app.uvicorn.port,
            "log_level": config.observability.logging.root_logger_level.lower(),
            "env_file": temp_envfile_path,
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
        if os.path.exists(temp_envfile_path):
            os.remove(temp_envfile_path)
        if os.path.exists(temp_yaml_config_path):
            os.remove(temp_yaml_config_path)


def _run_uvicorn(configuration: dict[str, tp.Any]) -> tp.NoReturn:
    uvicorn.run(
        "idu_api.urban_mcp.fastmcp_init:app",
        **configuration,
    )


if __name__ in ("__main__", "idu_api.urban_mcp.__main__"):
    try_load_envfile(os.environ.get("ENVFILE", ".env"))
    main()  # pylint: disable=no-value-for-parameter
