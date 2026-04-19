"""Social groups and values DTOs are defined here."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from idu_api.urban_api.dto.service_types import ServiceTypeDTO


@dataclass(frozen=True)
class SocGroupDTO:
    """DTO representing a social group classification."""

    soc_group_id: int
    name: str


@dataclass(frozen=True)
class SocGroupWithServiceTypesDTO:
    """DTO representing a social group with associated service types."""

    soc_group_id: int
    name: str
    service_types: list[dict[str, Any]]


@dataclass(frozen=True)
class SocValueDTO:
    """DTO representing a social value with normative and decree parameters."""

    soc_value_id: int
    name: str
    rank: int
    normative_value: float
    decree_value: float


@dataclass(frozen=True)
class SocValueIndicatorValueDTO:
    """DTO representing indicator values for a social value across territories."""

    soc_value_id: int
    soc_value_name: str
    territory_id: int
    territory_name: str
    year: int
    value: float
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SocValueWithServiceTypesDTO:
    """DTO representing a social value enriched with linked service types."""

    soc_value_id: int
    name: str
    rank: int
    normative_value: float
    decree_value: float
    service_types: list[ServiceTypeDTO]
