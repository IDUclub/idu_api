"""Database configuration class is defined here."""

from dataclasses import dataclass
from typing import Any

from idu_api.common.utils.secrets import SecretStr


@dataclass
class DBConfig:
    """Main database configuration class."""

    host: str
    port: int
    database: str
    user: str
    password: SecretStr
    pool_size: int
    debug: bool = False

    def __post_init__(self):
        """Convert password string in secret string."""
        self.password = SecretStr(self.password)


@dataclass
class MultipleDBsConfig:
    """Configuration for master and optional replica databases."""

    master: DBConfig
    replicas: list[DBConfig] | None = None

    def __post_init__(self):
        """Convert nested dicts into DBConfig instances."""
        _dict_to_dataclass(self, "master", DBConfig)
        if self.replicas is not None:
            _list_dict_to_dataclasses(self, "replicas", DBConfig)


def _list_dict_to_dataclasses(config_entry: Any, field_name: str, need_type: type) -> None:
    """Convert list of dicts in a field to a list of dataclass instances."""
    list_dict = getattr(config_entry, field_name)
    for i in range(len(list_dict)):  # pylint: disable=consider-using-enumerate
        if isinstance(list_dict[i], dict):
            list_dict[i] = need_type(**list_dict[i])


def _dict_to_dataclass(config_entry: Any, field_name: str, need_type: type) -> None:
    """Convert a dict field into a dataclass instance."""
    value = getattr(config_entry, field_name)
    if isinstance(value, dict):
        setattr(config_entry, field_name, need_type(**value))
