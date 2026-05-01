"""Hexagons DTOs are defined here."""

from dataclasses import asdict, dataclass
from typing import Any

import shapely.geometry as geom
from shapely.wkb import loads as wkb_loads

from idu_api.urban_api.dto.indicators import ScenarioIndicatorValueDTO


@dataclass
class HexagonDTO:
    """DTO representing a spatial hexagon with geometry and territory metadata."""

    hexagon_id: int
    territory_id: int
    territory_name: str
    geometry: geom.Polygon | geom.MultiPolygon
    centre_point: geom.Point
    properties: dict[str, Any] | None

    def __post_init__(self) -> None:
        """Normalize geometry and centre point from WKB and ensure geometry is set."""
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict:
        """Serialize DTO to a GeoJSON-like dictionary."""
        hexagon = asdict(self)
        del hexagon["territory_id"]
        del hexagon["territory_name"]
        return hexagon


@dataclass
class HexagonWithIndicatorsDTO:
    """DTO representing a hexagon enriched with indicator values."""

    hexagon_id: int
    geometry: geom.Polygon | geom.MultiPolygon
    centre_point: geom.Point
    indicators: [ScenarioIndicatorValueDTO]

    def __post_init__(self) -> None:
        """Normalize geometry and centre point from WKB and ensure geometry is set."""
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self) -> dict:
        """Serialize DTO to a GeoJSON-like dictionary."""
        return asdict(self)
