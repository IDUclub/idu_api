"""Object geometries DTOs are defined here."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import shapely.geometry as geom
from shapely.wkb import loads as wkb_loads

Geom = geom.Polygon | geom.MultiPolygon | geom.Point | geom.LineString | geom.MultiLineString


@dataclass
class ObjectGeometryDTO:
    """DTO representing a spatial object geometry with metadata and location info."""

    object_geometry_id: int
    territory_id: int
    territory_name: str
    address: str | None
    osm_id: str | None
    geometry: Geom
    centre_point: geom.Point
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Normalize geometry and centre point from WKB and ensure geometry is set."""
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        """Serialize DTO to a GeoJSON-like dictionary."""
        geometry = asdict(self)
        geometry["territory"] = {"id": geometry.pop("territory_id"), "name": geometry.pop("territory_name")}
        return geometry


@dataclass
class ScenarioGeometryDTO(ObjectGeometryDTO):
    """DTO representing an object geometry within a scenario context."""

    is_scenario_object: bool
    is_locked: bool = False


@dataclass
class GeometryWithAllObjectsDTO:
    """DTO representing geometry enriched with related physical objects and services."""

    object_geometry_id: int
    territory_id: int
    territory_name: str
    address: str | None
    osm_id: str | None
    geometry: Geom
    centre_point: geom.Point
    physical_objects: list[dict[str, Any]]
    services: list[dict[str, Any]]

    def __post_init__(self) -> None:
        """Normalize geometry and centre point from WKB and ensure geometry is set."""
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        """Serialize DTO to a GeoJSON-like dictionary."""
        obj = asdict(self)
        obj["territory"] = {"id": obj.pop("territory_id"), "name": obj.pop("territory_name")}
        return obj


@dataclass
class ScenarioGeometryWithAllObjectsDTO(GeometryWithAllObjectsDTO):
    """DTO representing scenario geometry with associated objects and services."""

    is_scenario_object: bool
    physical_objects: list[dict[str, Any]]
    services: list[dict[str, Any]]
    is_locked: bool = False
