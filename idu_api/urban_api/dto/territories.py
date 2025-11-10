"""Territories DTOs are defined here."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import shapely.geometry as geom
from shapely.wkb import loads as wkb_loads

from idu_api.urban_api.dto.indicators import BinnedIndicatorValueDTO, IndicatorValueDTO
from idu_api.urban_api.dto.normatives import NormativeDTO


@dataclass(frozen=True)
class TerritoryTypeDTO:
    """Territory type DTO used to transfer territory type data."""

    territory_type_id: int | None
    name: str


@dataclass(frozen=True)
class TargetCityTypeDTO:
    """Target city type DTO used to transfer target city type data."""

    target_city_type_id: int | None
    name: str
    description: str


@dataclass
class TerritoryDTO:  # pylint: disable=too-many-instance-attributes
    """Territory DTO used to transfer territory data."""

    territory_id: int
    territory_type_id: int
    territory_type_name: str
    parent_id: int
    parent_name: str
    name: str
    geometry: geom.Polygon | geom.MultiPolygon | geom.Point
    level: int
    properties: dict[str, Any] | None
    centre_point: geom.Point
    admin_center_id: int | None
    admin_center_name: str | None
    target_city_type_id: int | None
    target_city_type_name: str | None
    target_city_type_description: str | None
    okato_code: str | None
    oktmo_code: str | None
    is_city: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        territory = asdict(self)
        territory["territory_type"] = {
            "id": territory.pop("territory_type_id"),
            "name": territory.pop("territory_type_name"),
        }
        territory["parent"] = {
            "id": territory.pop("parent_id"),
            "name": territory.pop("parent_name"),
        }
        territory["admin_center"] = (
            {
                "id": territory.pop("admin_center_id"),
                "name": territory.pop("admin_center_name"),
            }
            if territory["admin_center_id"] is not None
            else None
        )
        territory["target_city_type"] = (
            {
                "id": territory.pop("target_city_type_id"),
                "name": territory.pop("target_city_type_name"),
                "description": territory.pop("target_city_type_description"),
            }
            if territory["target_city_type_id"] is not None
            else None
        )
        return territory


@dataclass(frozen=True)
class TerritoryWithoutGeometryDTO:  # pylint: disable=too-many-instance-attributes
    """Territory DTO used to transfer territory data without geometry."""

    territory_id: int
    territory_type_id: int
    territory_type_name: str
    parent_id: int
    parent_name: str
    name: str
    level: int
    properties: dict[str, Any]
    admin_center_id: int | None
    admin_center_name: str | None
    target_city_type_id: int | None
    target_city_type_name: str | None
    target_city_type_description: str | None
    okato_code: str | None
    oktmo_code: str | None
    is_city: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TerritoryTreeWithoutGeometryDTO(TerritoryWithoutGeometryDTO):
    """Territories Tree DTO used to transfer territory data without geometry."""

    children: list["TerritoryTreeWithoutGeometryDTO"]


@dataclass
class TerritoryWithIndicatorsDTO:
    """Territory DTO used to transfer short territory data with list of indicators."""

    territory_id: int
    name: str
    territory_type_id: int
    territory_type_name: str
    is_city: bool
    geometry: geom.Polygon | geom.MultiPolygon | geom.Point
    centre_point: geom.Point
    indicators: list[IndicatorValueDTO]

    def __post_init__(self) -> None:
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        territory = asdict(self)
        territory["territory_type"] = {
            "id": territory.pop("territory_type_id"),
            "name": territory.pop("territory_type_name"),
        }
        territory["centre_point"] = geom.mapping(self.centre_point)
        territory["indicators"] = [
            {
                "indicator_id": ind.indicator_id,
                "name_full": ind.name_full,
                "measurement_unit_name": ind.measurement_unit_name,
                "level": ind.level,
                "list_label": ind.list_label,
                "date_value": ind.date_value,
                "value": ind.value,
                "value_type": ind.value_type,
                "information_source": ind.information_source,
            }
            for ind in self.indicators
        ]
        return territory


@dataclass
class TerritoryWithBinnedIndicatorsDTO(TerritoryWithIndicatorsDTO):
    """Territory DTO used to transfer short territory data with list of indicators."""

    indicators: list[BinnedIndicatorValueDTO]

    def to_geojson_dict(self) -> dict[str, Any]:
        territory = asdict(self)
        territory["territory_type"] = {
            "id": territory.pop("territory_type_id"),
            "name": territory.pop("territory_type_name"),
        }
        territory["centre_point"] = geom.mapping(self.centre_point)
        territory["indicators"] = [
            {
                "indicator_id": ind.indicator_id,
                "name_full": ind.name_full,
                "measurement_unit_name": ind.measurement_unit_name,
                "level": ind.level,
                "list_label": ind.list_label,
                "date_value": ind.date_value,
                "value": ind.value,
                "value_type": ind.value_type,
                "information_source": ind.information_source,
                "binned_min_value": ind.binned_min_value,
                "binned_max_value": ind.binned_max_value,
            }
            for ind in self.indicators
        ]
        return territory


@dataclass
class TerritoryWithNormativesDTO:
    """Territory DTO used to transfer short territory data with list of indicators."""

    territory_id: int
    name: str
    territory_type_id: int
    territory_type_name: str
    is_city: bool
    geometry: geom.Polygon | geom.MultiPolygon | geom.Point
    centre_point: geom.Point
    normatives: list[NormativeDTO]

    def __post_init__(self) -> None:
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        territory = asdict(self)
        territory["territory_type"] = {
            "id": territory.pop("territory_type_id"),
            "name": territory.pop("territory_type_name"),
        }
        territory["centre_point"] = geom.mapping(self.centre_point)
        territory["normatives"] = [
            {
                "name": norm.urban_function_name if norm.service_type_name is None else norm.service_type_name,
                "year": norm.year,
                "normative_type": norm.normative_type,
                "radius_availability_meters": norm.radius_availability_meters,
                "time_availability_minutes": norm.time_availability_minutes,
                "services_per_1000_normative": norm.services_per_1000_normative,
                "services_capacity_per_1000_normative": norm.services_capacity_per_1000_normative,
                "is_regulated": norm.is_regulated,
            }
            for norm in self.normatives
        ]
        return territory
