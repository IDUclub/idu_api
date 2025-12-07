"""Bindings DTOs are defined here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShortTerritoryIndicatorBindDTO:
    indicator_id: int
    indicator_name: str
    measurement_unit_name: str | None
    min_value: float
    max_value: float


@dataclass(frozen=True)
class TerritoryIndicatorBindDTO:  # pylint: disable=too-many-instance-attributes
    indicator_id: int
    indicator_name: str
    indicator_parent_id: int | None
    indicator_level: int
    indicator_list_label: str
    measurement_unit_id: int | None
    measurement_unit_name: str | None
    territory_id: int
    territory_name: str
    territory_level: int
    min_value: float
    max_value: float
