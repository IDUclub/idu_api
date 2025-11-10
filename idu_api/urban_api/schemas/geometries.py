"""Geojson response models are defined here."""

import json
from typing import Any, Literal, TypeVar

import shapely
import shapely.geometry as geom
import structlog
from pydantic import BaseModel, Field, field_validator, model_validator

_BaseGeomTypes = (
    geom.Point | geom.MultiPoint | geom.Polygon | geom.MultiPolygon | geom.LineString | geom.MultiLineString
)

_logger: structlog.stdlib.BoundLogger = structlog.get_logger("geometry_schemas")


class AllPossibleGeometry(BaseModel):
    """Geometry representation for GeoJSON model (all valid geometry types)."""

    type: Literal[
        "Point", "MultiPoint", "Polygon", "MultiPolygon", "LineString", "MultiLineString", "GeometryCollection"
    ] = Field(examples=["Polygon"])
    coordinates: list[Any] | None = Field(
        default=None,
        description="Coordinates for non-GeometryCollection types.",
        examples=[
            [
                [
                    [30.22, 59.86],
                    [30.22, 59.85],
                    [30.25, 59.85],
                    [30.25, 59.86],
                    [30.22, 59.86],
                ]
            ]
        ],
    )
    geometries: list[dict] | None = Field(
        default=None,
        description="List of geometries for GeometryCollection.",
        examples=[
            [
                {"type": "Point", "coordinates": [100.0, 0.0]},
                {"type": "LineString", "coordinates": [[101.0, 0.0], [102.0, 1.0]]},
            ]
        ],
    )
    _shapely_geom: _BaseGeomTypes | geom.GeometryCollection | None = None

    @model_validator(mode="after")
    def validate_geometry(self) -> "AllPossibleGeometry":
        if self.type == "GeometryCollection":
            if self.geometries is None:
                raise ValueError("GeometryCollection must have 'geometries'.")
            if self.coordinates is not None:
                raise ValueError("GeometryCollection cannot have 'coordinates'.")
        else:
            if self.coordinates is None:
                raise ValueError(f"{self.type} must have 'coordinates'.")
            if self.geometries is not None:
                raise ValueError(f"{self.type} cannot have 'geometries'.")
        return self

    def as_shapely_geometry(self) -> geom.base.BaseGeometry:
        if self._shapely_geom is None:
            if self.type == "GeometryCollection":
                geometries = [AllPossibleGeometry(**g).as_shapely_geometry() for g in self.geometries]
                self._shapely_geom = geom.GeometryCollection(geometries)
            else:
                self._shapely_geom = shapely.from_geojson(
                    json.dumps({"type": self.type, "coordinates": self.coordinates})
                )
        return self._shapely_geom

    @classmethod
    def from_shapely_geometry(cls, geometry: _BaseGeomTypes | geom.GeometryCollection | None) -> "AllPossibleGeometry":
        if geometry is None:
            return None
        return cls(**geom.mapping(geometry))


class Geometry(BaseModel):
    """
    Geometry representation for GeoJSON model appliable for points, polygons, multipolygons and linestrings.
    """

    type: Literal["Point", "MultiPoint", "Polygon", "MultiPolygon", "LineString", "MultiLineString"] = Field(
        examples=["Polygon"]
    )
    coordinates: list[Any] = Field(
        description="list[float] for Point,\n" "list[list[list[float]]] for Polygon",
        examples=[
            [
                [
                    [30.22, 59.86],
                    [30.22, 59.85],
                    [30.25, 59.85],
                    [30.25, 59.86],
                    [30.22, 59.86],
                ]
            ]
        ],
    )
    _shapely_geom: _BaseGeomTypes | None = None

    def as_shapely_geometry(self) -> _BaseGeomTypes:
        """
        Return Shapely geometry object from the parsed geometry.
        """
        if self._shapely_geom is None:
            self._shapely_geom = shapely.from_geojson(json.dumps({"type": self.type, "coordinates": self.coordinates}))
        return self._shapely_geom

    @classmethod
    def from_shapely_geometry(cls, geometry: _BaseGeomTypes | None) -> "Geometry":
        """
        Construct Geometry model from shapely geometry.
        """
        if geometry is None:
            return None
        return cls(**geom.mapping(geometry))


class Point(Geometry):
    """
    Geometry representation for GeoJSON model appliable for points only.
    """

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(description="list[float]", examples=[[30.22, 59.86]])
    _shapely_geom: _BaseGeomTypes | None = None


T = TypeVar("T", bound="GeometryValidationModel")


class GeometryValidationModel(BaseModel):
    """Base model with geometry validation methods."""

    geometry: Geometry | None = None
    centre_point: Point | None = None

    @classmethod
    @field_validator("geometry")
    def validate_geometry(cls, geometry: "Geometry") -> "Geometry":
        """Validate that given geometry is valid by creating a Shapely object."""
        if geometry:
            try:
                geometry.as_shapely_geometry()
            except (AttributeError, ValueError, TypeError) as exc:
                _logger.debug("Exception on passing geometry: {!r}", exc)
                raise ValueError("Invalid geometry passed") from exc
        return geometry

    @classmethod
    @field_validator("centre_point")
    def validate_centre_point(cls, centre_point: Point | None) -> Point | None:
        """Validate that given centre_point is a valid Point geometry."""
        if centre_point:
            if centre_point.type != "Point":
                raise ValueError("Only Point geometry is accepted for centre_point")
            try:
                centre_point.as_shapely_geometry()
            except (AttributeError, ValueError, TypeError) as exc:
                _logger.debug("Exception on passing geometry: {!r}", exc)
                raise ValueError("Invalid centre_point passed") from exc
        return centre_point

    @model_validator(mode="after")
    def validate_centre_point_from_geometry(self) -> T:
        """Use the geometry's centroid for centre_point if it is missing."""
        if self.centre_point is None and self.geometry:
            self.centre_point = Geometry.from_shapely_geometry(self.geometry.as_shapely_geometry().centroid)
        return self


class NotPointGeometryValidationModel(BaseModel):
    """Base model with geometry validation methods (without points)."""

    geometry: Geometry | None = None

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, geometry: "Geometry") -> "Geometry":
        """Validate that given geometry is valid by creating a Shapely object."""
        if geometry:
            try:
                geometry.as_shapely_geometry()
            except (AttributeError, ValueError, TypeError) as exc:
                _logger.debug("Exception on passing geometry: {!r}", exc)
                raise ValueError("Invalid geometry passed") from exc
        return geometry
