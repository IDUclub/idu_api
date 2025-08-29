"""Hexagons schemas are defined here."""

from typing import Any

from pydantic import BaseModel, Field

from idu_api.urban_api.dto import HexagonDTO
from idu_api.urban_api.schemas.geometries import Geometry, GeometryValidationModel, Point
from idu_api.urban_api.schemas.short_models import ShortProjectIndicatorValue, ShortTerritory


class Hexagon(BaseModel):
    """Hexagon with all its attributes."""

    hexagon_id: int = Field(..., description="hexagon identifier", examples=[1])
    territory: ShortTerritory
    geometry: Geometry
    centre_point: Point
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="hexagon properties",
        examples=[{"attribute_name": "attribute_value"}],
    )

    @classmethod
    def from_dto(cls, dto: HexagonDTO) -> "Hexagon":
        """Construct from DTO"""

        return cls(
            hexagon_id=dto.hexagon_id,
            territory=ShortTerritory(
                id=dto.territory_id,
                name=dto.territory_name,
            ),
            geometry=Geometry.from_shapely_geometry(dto.geometry),
            centre_point=Point.from_shapely_geometry(dto.centre_point),
            properties=dto.properties,
        )


class HexagonAttributes(BaseModel):
    """Hexagon with all its attributes."""

    hexagon_id: int = Field(..., description="hexagon identifier", examples=[1])
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="hexagon properties",
        examples=[{"attribute_name": "attribute_value"}],
    )


class HexagonPost(GeometryValidationModel):
    """Hexagon schema for POST requests."""

    geometry: Geometry
    centre_point: Point | None = None
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="hexagon properties",
        examples=[{"attribute_name": "attribute_value"}],
    )


class HexagonWithIndicators(BaseModel):
    """Short hexagon info with geometry and all indicator values."""

    hexagon_id: int = Field(..., examples=[1])
    indicators: list[ShortProjectIndicatorValue]
