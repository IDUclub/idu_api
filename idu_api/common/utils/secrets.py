"""Basic functionality to work with sensitive data in configs is defined here."""

import os
import re
from typing import Any

import yaml

_env_re = re.compile(r"^!env\((?P<env_var>.+)\)$")


class SecretStr(str):
    """String value which returns "<REDACTED>" on str() and repr() calls.

    If given value matches pattern `^!env\\(.+\\)$` then try to get value from environment variables by the given name.

    To get a value inside one should use `get_secret_value` method.
    """

    def __new__(cls, other: Any):
        if isinstance(other, SecretStr):
            return super().__new__(cls, other.get_secret_value())
        if isinstance(other, str):
            if (m := _env_re.match(other)) is not None:
                env_var = m.group("env_var")
                if env_var in os.environ:
                    other = os.environ[env_var]
                else:
                    print(
                        f"CAUTION: secret variable '{other}' looks like a mapping from env,"
                        f" but no '{env_var} value is found'"
                    )
            return super().__new__(cls, other)

    def __str__(self) -> str:
        return "<REDACTED>"

    def __repr__(self) -> str:
        return "'<REDACTED!r>'"

    def get_secret_value(self) -> str:
        return super().__str__()


def representSecretStrYAML(dumper: yaml.Dumper, s: SecretStr):
    return dumper.represent_str(s.get_secret_value())


yaml.add_representer(SecretStr, representSecretStrYAML)
