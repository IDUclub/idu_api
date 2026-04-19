"""Buffers DTOs are defined here."""

from dataclasses import asdict, dataclass
from typing import Any

import shapely.geometry as geom
from shapely.wkb import loads as wkb_loads


@dataclass(frozen=True)
class BufferTypeDTO:
    """DTO describing a buffer type."""

    buffer_type_id: int
    name: str
    description: str | None


@dataclass(frozen=True)
class DefaultBufferValueDTO:
    """DTO for default buffer values by object and service types."""

    buffer_type_id: int
    buffer_type_name: str
    buffer_type_description: str | None
    physical_object_type_id: int | None
    physical_object_type_name: str | None
    service_type_id: int | None
    service_type_name: str | None
    buffer_value: float


@dataclass
class BufferDTO:  # pylint: disable=too-many-instance-attributes
    """DTO representing a spatial buffer with related urban object data."""

    buffer_type_id: int
    buffer_type_name: str
    buffer_type_description: str | None
    urban_object_id: int
    physical_object_id: int
    physical_object_name: str
    physical_object_type_id: int
    physical_object_type_name: str
    object_geometry_id: int
    territory_id: int
    territory_name: str
    service_id: int | None
    service_name: str | None
    service_type_id: int | None
    service_type_name: str | None
    geometry: geom.Polygon | geom.MultiPolygon
    is_custom: bool

    def __post_init__(self) -> None:
        """Convert geometry from WKB bytes to shapely object if needed."""
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict[str, Any]:
        """Serialize DTO to a GeoJSON-like dictionary."""
        buffer = asdict(self)

        buffer["buffer_type"] = {
            "id": buffer.pop("buffer_type_id"),
            "name": buffer.pop("buffer_type_name"),
            "description": buffer.pop("buffer_type_description"),
        }
        buffer["urban_object"] = {
            "id": buffer.pop("urban_object_id"),
            "physical_object": {
                "id": buffer.pop("physical_object_id"),
                "name": buffer.pop("physical_object_name"),
                "type": {
                    "id": buffer.pop("physical_object_type_id"),
                    "name": buffer.pop("physical_object_type_name"),
                },
            },
            "object_geometry": {
                "id": buffer.pop("object_geometry_id"),
                "territory": {
                    "id": buffer.pop("territory_id"),
                    "name": buffer.pop("territory_name"),
                },
            },
        }
        service = {
            "id": buffer.pop("service_id"),
            "name": buffer.pop("service_name"),
            "type": {
                "id": buffer.pop("service_type_id"),
                "name": buffer.pop("service_type_name"),
            },
        }
        buffer["urban_object"]["service"] = service if service["id"] is not None else None

        return buffer


@dataclass
class ScenarioBufferDTO(BufferDTO):
    """Extended buffer DTO with scenario-specific attributes."""

    is_scenario_object: bool
    is_locked: bool
