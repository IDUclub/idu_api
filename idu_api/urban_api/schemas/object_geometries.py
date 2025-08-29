"""Object geometries schemas are defined here."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

from idu_api.urban_api.dto import ObjectGeometryDTO, ScenarioGeometryDTO
from idu_api.urban_api.schemas.geometries import Geometry, GeometryValidationModel, Point
from idu_api.urban_api.schemas.short_models import (
    ShortPhysicalObject,
    ShortScenarioPhysicalObject,
    ShortScenarioService,
    ShortService,
    ShortTerritory,
)


class ObjectGeometry(BaseModel):
    """Object geometry with all its attributes."""

    object_geometry_id: int = Field(..., examples=[1])
    territory: ShortTerritory
    address: str | None = Field(..., description="physical object address", examples=["--"])
    osm_id: str | None = Field(..., description="open street map identifier", examples=["1"])
    geometry: Geometry
    centre_point: Point
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the geometry was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the geometry was last updated"
    )

    @classmethod
    def from_dto(cls, dto: ObjectGeometryDTO) -> "ObjectGeometry":
        """
        Construct from DTO.
        """
        return cls(
            object_geometry_id=dto.object_geometry_id,
            territory=ShortTerritory(id=dto.territory_id, name=dto.territory_name),
            address=dto.address,
            osm_id=dto.osm_id,
            geometry=Geometry.from_shapely_geometry(dto.geometry),
            centre_point=Point.from_shapely_geometry(dto.centre_point),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class ScenarioObjectGeometry(ObjectGeometry):
    """Object geometry with all its attributes."""

    is_scenario_object: bool = Field(..., description="boolean parameter to determine scenario object")

    @classmethod
    def from_dto(cls, dto: ScenarioGeometryDTO) -> "ScenarioObjectGeometry":
        """
        Construct from DTO.
        """
        return cls(
            object_geometry_id=dto.object_geometry_id,
            territory=ShortTerritory(id=dto.territory_id, name=dto.territory_name),
            address=dto.address,
            osm_id=dto.osm_id,
            geometry=Geometry.from_shapely_geometry(dto.geometry),
            centre_point=Point.from_shapely_geometry(dto.centre_point),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            is_scenario_object=dto.is_scenario_object,
        )


class ObjectGeometryPost(GeometryValidationModel):
    """Object geometry schema for POST requests."""

    territory_id: int = Field(..., examples=[1])
    geometry: Geometry
    centre_point: Point | None = None
    address: str | None = Field(None, description="physical object address", examples=["--"])
    osm_id: str | None = Field(None, description="open street map identifier", examples=["1"])


class ObjectGeometryPut(GeometryValidationModel):
    """Object geometry schema for PUT requests."""

    territory_id: int = Field(..., examples=[1])
    geometry: Geometry
    centre_point: Point
    address: str | None = Field(..., description="physical object address", examples=["--"])
    osm_id: str | None = Field(..., description="open street map identifier", examples=["1"])


class ObjectGeometryPatch(GeometryValidationModel):
    """Object geometry schema for PATCH requests."""

    territory_id: int | None = Field(None, examples=[1])
    geometry: Geometry | None = None
    centre_point: Point | None = None
    address: str | None = Field(None, description="physical object address", examples=["--"])
    osm_id: str | None = Field(None, description="open street map identifier", examples=["1"])

    @model_validator(mode="before")
    @classmethod
    def check_empty_request(cls, values):
        """
        Ensure the request body is not empty.
        """
        if not values:
            raise ValueError("request body cannot be empty")
        return values


class GeometryAttributes(BaseModel):
    """Object geometry schema (but without geometry columns)."""

    object_geometry_id: int = Field(..., examples=[1])
    territory: ShortTerritory
    address: str | None = Field(..., description="physical object address", examples=["--"])
    osm_id: str | None = Field(..., description="open street map identifier", examples=["1"])
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the geometry was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the geometry was last updated"
    )


class ScenarioGeometryAttributes(GeometryAttributes):
    """Scenario object geometry schema (but without geometry columns)."""

    is_scenario_object: bool = Field(..., description="boolean parameter to determine scenario object")


class AllObjects(BaseModel):
    """Object geometry with all its physical objects and services (but without geometry columns...)."""

    object_geometry_id: int = Field(..., examples=[1])
    territory: ShortTerritory
    address: str | None = Field(..., description="physical object address", examples=["--"])
    osm_id: str | None = Field(..., description="open street map identifier", examples=["1"])
    physical_objects: list[ShortPhysicalObject]
    services: list[ShortService]


class ScenarioAllObjects(AllObjects):
    """Scenario object geometry with all its physical objects and services (but without geometry columns...)."""

    is_scenario_object: bool = Field(..., description="boolean parameter to determine scenario object")
    physical_objects: list[ShortScenarioPhysicalObject]
    services: list[ShortScenarioService]
