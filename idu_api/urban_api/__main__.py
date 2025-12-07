import os
import tempfile
import typing as tp

import click
import uvicorn

from .config import UrbanAPIConfig
from .utils.dotenv import try_load_envfile

LogLevel = tp.Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"]


def logger_from_str(logger_text: str) -> list[tuple[LogLevel, str]]:
    """
    Helper function to deconstruct string input argument(s) to logger configuration.

    Examples:
    - logger_from_str("ERROR,errors.log") -> [("ERROR", "errors.log)]
    - logger_from_str("ERROR,errors.log;INFO,info.log") -> [("ERROR", "errors.log), ("INFO", "info.log")]
    """
    res = []
    for item in logger_text.split(";"):
        assert "," in item, f'logger text must be in format "LEVEL,filename" - current value is "{logger_text}"'
        level, filename = item.split(",", 1)
        level = level.upper()
        res.append((level, filename))  # type: ignore
    return res


def _run_uvicorn(configuration: dict[str, tp.Any]) -> tp.NoReturn:
    uvicorn.run(
        "idu_api.urban_api.fastapi_init:app",
        **configuration,
    )


@click.command("Run urban api service")
@click.option(
    "--port",
    "-p",
    envvar="PORT",
    type=int,
    show_envvar=True,
    help="Service port number",
)
@click.option(
    "--host",
    envvar="HOST",
    show_envvar=True,
    help="Service HOST address",
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Enable debug mode (auto-reload on change, traceback returned to user, etc.)",
)
@click.option(
    "--config_path",
    envvar="CONFIG_PATH",
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
    """
    Urban api backend service main function, performs configuration
    via config and command line + environment variables overrides.
    """
    print(
        "This is a simple method to run the API. You might want to use"
        " 'uvicorn idu_api.urban_api.fastapi_init:app' instead to configure more uvicorn options."
    )
    config = UrbanAPIConfig.load(config_path)
    if host is not None and host != config.app.host:
        print(f"Overwriting config host with '{host}'")
        config.app.host = host
    if port is not None and port != config.app.port:
        print(f"Overwriting config port with '{port}'")
        config.app.port = port
    if debug:
        print("Overwriting debug with 'True'")
        config.app.debug = True
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_yaml_config_path = temp_file.name
    config.dump(temp_yaml_config_path)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_envfile_path = temp_file.name
    with open(temp_envfile_path, "w", encoding="utf-8") as env_file:
        env_file.write(f"CONFIG_PATH={temp_yaml_config_path}\n")
    os.environ["CONFIG_PATH"] = temp_yaml_config_path
    try:
        uvicorn_config = {
            "host": config.app.host,
            "port": config.app.port,
            "log_level": config.observability.logging.root_logger_level.lower(),
            "env_file": temp_envfile_path,
        }
        if config.app.debug:
            try:
                _run_uvicorn(uvicorn_config | {"reload": True})
            except:  # pylint: disable=bare-except
                print("Debug reload is disabled")
                _run_uvicorn(uvicorn_config)
        else:
            _run_uvicorn(uvicorn_config)
    finally:
        if os.path.exists(temp_envfile_path):
            os.remove(temp_envfile_path)
        if os.path.exists(temp_yaml_config_path):
            os.remove(temp_yaml_config_path)


if __name__ in ("__main__", "idu_api.urban_api.__main__"):
    try_load_envfile(os.environ.get("ENVFILE", ".env"))
    main()  # pylint: disable=no-value-for-parameter
