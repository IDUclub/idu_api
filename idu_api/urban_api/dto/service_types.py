"""Service types DTOs are defined here."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, Self


@dataclass(frozen=True)
class ServiceTypeDTO:
    """DTO representing a service type with functional and capacity metadata."""

    service_type_id: int
    urban_function_id: int | None
    urban_function_name: str | None
    name: str
    capacity_modeled: int | None
    code: str
    infrastructure_type: Literal["basic", "additional", "comfort"] | None
    properties: dict[str, Any]

    @classmethod
    def fields(cls) -> Iterable[str]:
        """Return list of field names for the DTO."""
        return cls.__annotations__.keys()


@dataclass(frozen=True)
class UrbanFunctionDTO:
    """DTO representing an urban function and its hierarchical structure."""

    urban_function_id: int
    parent_id: int | None
    parent_urban_function_name: str | None
    name: str
    level: int
    list_label: str
    code: str


@dataclass(frozen=True)
class ServiceTypesHierarchyDTO:
    """DTO representing hierarchical structure of urban functions and service types."""

    urban_function_id: int
    parent_id: int | None
    name: str
    level: int
    list_label: str
    code: str
    children: list[Self | ServiceTypeDTO]
