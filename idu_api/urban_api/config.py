"""Application configuration class is defined here."""

from collections import OrderedDict
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Literal, TextIO, Type, Union, get_origin

import yaml

from idu_api.common.db.config import DBConfig, MultipleDBsConfig
from idu_api.common.utils.secrets import SecretStr, representSecretStrYAML
from idu_api.urban_api.utils.observability import (
    ExporterConfig,
    FileLogger,
    JaegerConfig,
    LoggingConfig,
    ObservabilityConfig,
    PrometheusConfig,
)


@dataclass
class CORSConfig:
    allow_origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    allow_credentials: bool


@dataclass
class AppConfig:
    host: str
    port: int
    debug: bool
    cors: CORSConfig


@dataclass
class AuthConfig:
    url: str
    validate: bool
    cache_size: int
    cache_ttl: int


@dataclass
class FileServerConfig:
    url: str
    projects_bucket: str
    access_key: str
    secret_key: SecretStr
    region_name: str
    connect_timeout: int
    read_timeout: int

    def __post_init__(self):
        if not self.url.startswith("http"):
            self.url = "http://" + self.url
        self.secret_key = SecretStr(self.secret_key)


@dataclass
class ExternalServicesConfig:
    gen_planner_api: str
    hextech_api: str


@dataclass
class BrokerConfig:
    client_id: str
    bootstrap_servers: str
    schema_registry_url: str
    enable_idempotence: bool
    max_in_flight: int


@dataclass
class UrbanAPIConfig:
    app: AppConfig
    db: MultipleDBsConfig
    auth: AuthConfig
    fileserver: FileServerConfig
    external: ExternalServicesConfig
    observability: ObservabilityConfig
    broker: BrokerConfig

    def to_order_dict(self) -> OrderedDict:
        """OrderDict transformer."""

        def to_ordered_dict_recursive(obj) -> OrderedDict:
            """Recursive OrderDict transformer."""

            if isinstance(obj, (dict, OrderedDict)):
                return OrderedDict((k, to_ordered_dict_recursive(v)) for k, v in obj.items())
            if isinstance(obj, list):
                return [to_ordered_dict_recursive(item) for item in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return OrderedDict(
                    (field, to_ordered_dict_recursive(getattr(obj, field))) for field in obj.__dataclass_fields__
                )
            return obj

        return OrderedDict([(section, to_ordered_dict_recursive(getattr(self, section))) for section in asdict(self)])

    def dump(self, file: str | Path | TextIO) -> None:
        """Export current configuration to a file"""

        class OrderedDumper(yaml.SafeDumper):
            def represent_dict_preserve_order(self, data):
                return self.represent_dict(data.items())

            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow, False)

        OrderedDumper.add_representer(OrderedDict, OrderedDumper.represent_dict_preserve_order)
        OrderedDumper.add_representer(SecretStr, representSecretStrYAML)

        if isinstance(file, (str, Path)):
            with open(str(file), "w", encoding="utf-8") as file_w:
                yaml.dump(self.to_order_dict(), file_w, Dumper=OrderedDumper)
        else:
            yaml.dump(self.to_order_dict(), file, Dumper=OrderedDumper)

    @classmethod
    def example(cls) -> "UrbanAPIConfig":
        """Generate an example of configuration."""

        return cls(
            app=AppConfig(host="0.0.0.0", port=8000, debug=False, cors=CORSConfig(["*"], ["*"], ["*"], True)),
            db=MultipleDBsConfig(
                master=DBConfig(
                    host="localhost",
                    port=5432,
                    database="urban_db",
                    user="postgres",
                    password="postgres",
                    pool_size=15,
                    debug=True,
                ),
                replicas=[
                    DBConfig(
                        host="localhost",
                        port=5433,
                        user="readonly",
                        password="readonly",
                        database="urban_db",
                        pool_size=8,
                        debug=True,
                    )
                ],
            ),
            auth=AuthConfig(url="http://localhost:8086/introspect", validate=False, cache_size=100, cache_ttl=1800),
            fileserver=FileServerConfig(
                url="http://localhost:9000",
                projects_bucket="projects.images",
                access_key="",
                secret_key="",
                region_name="us-west-rack-2",
                connect_timeout=5,
                read_timeout=20,
            ),
            external=ExternalServicesConfig(
                hextech_api="http://localhost:8100", gen_planner_api="http://localhost:8101"
            ),
            observability=ObservabilityConfig(
                logging=LoggingConfig(
                    stderr_level="INFO",
                    exporter=ExporterConfig("http://127.0.0.1:4317", level="INFO"),
                    files=[FileLogger(filename="logs/info.log", level="INFO")],
                ),
                prometheus=PrometheusConfig(host="0.0.0.0", port=9090, urls_mapping={}),
                jaeger=JaegerConfig(endpoint="http://127.0.0.1:4318/v1/traces"),
            ),
            broker=BrokerConfig(
                client_id="urban-api",
                bootstrap_servers="localhost:9092",
                schema_registry_url="http://localhost:8100",
                enable_idempotence=False,
                max_in_flight=5,
            ),
        )

    @classmethod
    def load(cls, file: str | Path | TextIO) -> "UrbanAPIConfig":
        """Import config from the given filename or raise `ValueError` on error."""

        try:
            if isinstance(file, (str, Path)):
                with open(file, "r", encoding="utf-8") as file_r:
                    data = yaml.safe_load(file_r)
            else:
                data = yaml.safe_load(file)
        except Exception as exc:
            raise ValueError(f"Could not read app config file: {file}") from exc

        try:
            return UrbanAPIConfig._initialize_from_dict(UrbanAPIConfig, data)
        except Exception as e:
            raise RuntimeError(f"Could not initialize dependency configs: {e}") from e

    @staticmethod
    def _initialize_from_dict(t: Type, data: Any) -> Any:
        """Try to initialize given type field-by-field recursively with data from dictionary substituting {} and None
        if no value provided.
        """
        if get_origin(t) is Union or get_origin(t) is UnionType:  # both actually required
            for inner_type in t.__args__:
                if inner_type is NoneType and data is None:
                    return None
                try:
                    return UrbanAPIConfig._initialize_from_dict(inner_type, data)
                except Exception:  # pylint: disable=broad-except
                    pass
            raise ValueError(f"Cannot instanciate type '{t}' from {data}")

        if hasattr(t, "__origin__") and t.__origin__ is dict:
            return data

        if not isinstance(data, dict):
            if hasattr(t, "__origin__") and t.__origin__ is Literal and data in t.__args__:
                return data
            return t(data)

        init_dict = {}
        for fld in fields(t):
            inner_data = data.get(fld.name)
            if inner_data is None:
                if isinstance(fld.type, UnionType) and NoneType in fld.type.__args__:
                    init_dict[fld.name] = None
                    continue
                inner_data = {}
            else:
                init_dict[fld.name] = UrbanAPIConfig._initialize_from_dict(fld.type, inner_data)
        return t(**init_dict)

    @classmethod
    def from_file(cls, config_path: str) -> "UrbanAPIConfig":
        """Load configuration from the given path."""

        if not config_path or not Path(config_path).is_file():
            raise ValueError(f"Requested config is not a valid file: {config_path}")

        return cls.load(config_path)
