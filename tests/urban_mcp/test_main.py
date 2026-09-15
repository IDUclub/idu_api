"""Regression tests for module and console Urban MCP entrypoints."""

import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from dotenv import dotenv_values

from idu_api.urban_mcp import __main__ as entrypoint
from idu_api.urban_mcp.config import UrbanMCPConfig


@pytest.fixture(name="config_file")
def config_file_fixture(tmp_path):
    config = UrbanMCPConfig.example()
    config.app.uvicorn.reload = False
    config.app.debug = False
    path = tmp_path / "mcp.yaml"
    config.dump(path)
    return path


@pytest.fixture
def clean_environment(monkeypatch, tmp_path):
    for name in ("MCP_CONFIG_PATH", "CONFIG_PATH", "HOST", "PORT", "DEBUG", "ENVFILE"):
        # Record absent variables too: dotenv writes them without monkeypatch.
        monkeypatch.setenv(name, os.environ.get(name, ""))
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def test_import_does_not_load_environment_or_start_server(tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text("MCP_IMPORT_SIDE_EFFECT=loaded\n", encoding="utf-8")
    env = os.environ.copy()
    env.pop("MCP_IMPORT_SIDE_EFFECT", None)
    env["ENVFILE"] = str(envfile)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import idu_api.urban_mcp.__main__; "
            "assert 'MCP_IMPORT_SIDE_EFFECT' not in os.environ; print('imported')",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported"


@pytest.mark.usefixtures("clean_environment")
@pytest.mark.parametrize("entrypoint_kind", ["console", "module"])
@pytest.mark.parametrize("custom_envfile", [False, True])
def test_entrypoints_load_dotenv_before_parsing_options(
    monkeypatch, tmp_path, config_file, entrypoint_kind, custom_envfile
):
    envfile = tmp_path / ("custom.env" if custom_envfile else ".env")
    envfile.write_text(f"MCP_CONFIG_PATH={config_file.as_posix()}\nHOST=127.0.0.2\nPORT=8123\n", encoding="utf-8")
    if custom_envfile:
        monkeypatch.setenv("ENVFILE", str(envfile))
    calls = []

    def run_uvicorn(app, **kwargs):
        config_path = Path(os.environ["MCP_CONFIG_PATH"])
        env_path = Path(kwargs["env_file"])
        config = UrbanMCPConfig.load(config_path)
        assert app == "idu_api.urban_mcp.fastmcp_init:app"
        assert kwargs["host"] == config.app.uvicorn.host == "127.0.0.2"
        assert kwargs["port"] == config.app.uvicorn.port == 8123
        assert Path(dotenv_values(env_path)["MCP_CONFIG_PATH"]) == config_path
        assert "CONFIG_PATH" not in dotenv_values(env_path)
        calls.append((config_path, env_path))

    monkeypatch.setattr(entrypoint.uvicorn, "run", run_uvicorn)
    monkeypatch.setattr(sys, "argv", ["launch_urban_mcp"])
    with pytest.raises(SystemExit) as exc:
        if entrypoint_kind == "console":
            entrypoint.main()
        else:
            monkeypatch.delitem(sys.modules, "idu_api.urban_mcp.__main__")
            runpy.run_module("idu_api.urban_mcp", run_name="__main__")
    assert exc.value.code == 0
    assert len(calls) == 1
    assert all(not path.exists() for path in calls[0])
    assert os.environ["MCP_CONFIG_PATH"] == config_file.as_posix()


@pytest.mark.usefixtures("clean_environment")
def test_cli_options_override_environment_and_yaml(monkeypatch, config_file):
    monkeypatch.setenv("HOST", "127.0.0.2")
    monkeypatch.setenv("PORT", "8123")
    configs = []

    def run_uvicorn(_app, **kwargs):
        config = UrbanMCPConfig.load(os.environ["MCP_CONFIG_PATH"])
        assert kwargs["host"] == config.app.uvicorn.host == "127.0.0.3"
        assert kwargs["port"] == config.app.uvicorn.port == 8124
        assert config.app.debug is True
        configs.append(config)

    monkeypatch.setattr(entrypoint.uvicorn, "run", run_uvicorn)
    result = CliRunner().invoke(
        entrypoint.cli, ["--config_path", str(config_file), "--host", "127.0.0.3", "--port", "8124", "--debug"]
    )
    assert result.exit_code == 0, result.exception
    assert len(configs) == 1
    assert "MCP_CONFIG_PATH" not in os.environ
    assert UrbanMCPConfig.load(config_file).app.debug is False


@pytest.mark.usefixtures("clean_environment")
@pytest.mark.parametrize("reload", [False, True])
def test_startup_failure_cleans_files_and_restores_environment(monkeypatch, config_file, reload):
    config = UrbanMCPConfig.load(config_file)
    config.app.uvicorn.reload = reload
    config.dump(config_file)
    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_file))
    calls = []

    def fail_uvicorn(_app, **kwargs):
        paths = (Path(os.environ["MCP_CONFIG_PATH"]), Path(kwargs["env_file"]))
        assert all(path.exists() for path in paths)
        calls.append((kwargs.get("reload", False), paths))
        raise RuntimeError("Server startup failed")

    monkeypatch.setattr(entrypoint.uvicorn, "run", fail_uvicorn)
    result = CliRunner().invoke(entrypoint.cli, [])
    assert isinstance(result.exception, RuntimeError)
    assert [enabled for enabled, _ in calls] == ([True, False] if reload else [False])
    assert all(not path.exists() for _, paths in calls for path in paths)
    assert os.environ["MCP_CONFIG_PATH"] == str(config_file)


@pytest.mark.usefixtures("clean_environment")
def test_config_dump_failure_removes_temporary_directory(monkeypatch, config_file):
    paths = []

    def fail_dump(_config, path):
        paths.append(path)
        path.write_text("partial config", encoding="utf-8")
        raise OSError("Could not write config")

    monkeypatch.setattr(UrbanMCPConfig, "dump", fail_dump)
    result = CliRunner().invoke(entrypoint.cli, ["--config_path", str(config_file)])
    assert isinstance(result.exception, OSError)
    assert len(paths) == 1
    assert not paths[0].parent.exists()
    assert "MCP_CONFIG_PATH" not in os.environ
