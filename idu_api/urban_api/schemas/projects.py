"""Projects schemas are defined here."""

from datetime import date, datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator

from idu_api.urban_api.dto import ProjectDTO, ProjectPhasesDTO, ProjectTerritoryDTO
from idu_api.urban_api.schemas.geometries import Geometry, GeometryValidationModel, Point
from idu_api.urban_api.schemas.short_models import ShortProjectWithScenario, ShortScenario, ShortTerritory


class ProjectTerritory(BaseModel):
    """Project territory with all its attributes."""

    project_territory_id: int = Field(..., description="project territory id", examples=[1])
    project: ShortProjectWithScenario
    geometry: Geometry
    centre_point: Point | None = None
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project territory additional properties",
        examples=[{"attribute_name": "attribute_value"}],
    )

    @classmethod
    def from_dto(cls, dto: ProjectTerritoryDTO) -> "ProjectTerritory":
        """Construct from DTO"""

        return cls(
            project_territory_id=dto.project_territory_id,
            project=ShortProjectWithScenario(
                project_id=dto.project_id,
                name=dto.project_name,
                user_id=dto.project_user_id,
                region=ShortTerritory(id=dto.territory_id, name=dto.territory_name),
                base_scenario=ShortScenario(id=dto.scenario_id, name=dto.scenario_name),
            ),
            geometry=Geometry.from_shapely_geometry(dto.geometry),
            centre_point=Point.from_shapely_geometry(dto.centre_point),
            properties=dto.properties,
        )


class ProjectTerritoryPost(GeometryValidationModel):
    """Project territory schema for POST requests."""

    geometry: Geometry
    centre_point: Point | None = None
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project territory additional properties",
        examples=[{"attribute_name": "attribute_value"}],
    )


class Project(BaseModel):
    """Project with all its attributes."""

    project_id: int = Field(..., description="project identifier", examples=[1])
    user_id: str = Field(..., description="project creator identifier", examples=["admin@test.ru"])
    name: str = Field(..., description="project name", examples=["--"])
    territory: ShortTerritory
    base_scenario: ShortScenario | None
    description: str | None = Field(..., description="project description", examples=["--"])
    public: bool = Field(..., description="project publicity", examples=[True])
    is_regional: bool = Field(..., description="boolean parameter for regional projects", examples=[False])
    is_city: bool = Field(..., description="boolean parameter to determine city project")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project's additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="project created at")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="project updated at")

    @classmethod
    def from_dto(cls, dto: ProjectDTO) -> "Project":
        return cls(
            project_id=dto.project_id,
            user_id=dto.user_id,
            name=dto.name,
            territory=ShortTerritory(id=dto.territory_id, name=dto.territory_name),
            base_scenario=(
                ShortScenario(id=dto.scenario_id, name=dto.scenario_name) if dto.scenario_id is not None else None
            ),
            description=dto.description,
            public=dto.public,
            is_regional=dto.is_regional,
            is_city=dto.is_city,
            properties=dto.properties,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class ProjectPost(BaseModel):
    """Project schema for POST request."""

    name: str = Field(..., description="project name", examples=["--"])
    territory_id: int = Field(..., description="project region identifier", examples=[1])
    is_city: bool = Field(False, description="boolean parameter to determine city project")
    description: str | None = Field(None, description="project description", examples=["--"])
    public: bool = Field(..., description="project publicity", examples=[True])
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project's additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    is_regional: bool = Field(False, description="boolean parameter to determine regional project")
    territory: ProjectTerritoryPost | None

    @model_validator(mode="after")
    def check_project_territory(self) -> "ProjectPost":
        if self.is_regional and self.territory is not None:
            raise ValueError("regional projects cannot have their own territory")
        if not self.is_regional and self.territory is None:
            raise ValueError("non-regional projects must have a territory")
        return self


class ProjectPut(BaseModel):
    """Project schema for PUT request."""

    name: str = Field(..., description="project name", examples=["--"])
    description: str = Field(..., description="project description", examples=["--"])
    public: bool = Field(..., description="project publicity", examples=[True])
    properties: dict[str, Any] = Field(
        ...,
        description="project's additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )


class ProjectPatch(BaseModel):
    """Project schema for PATCH request."""

    name: str | None = Field(None, description="project name", examples=["--"])
    description: str | None = Field(None, description="project description", examples=["--"])
    public: bool | None = Field(None, description="project publicity", examples=[True])
    properties: dict[str, Any] | None = Field(
        None,
        description="project's additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )

    @model_validator(mode="before")
    @classmethod
    def check_empty_request(cls, values):
        """Ensure the request body is not empty."""
        if not values:
            raise ValueError("request body cannot be empty")
        return values


class ProjectPhases(BaseModel):
    """Project's phases schema."""

    actual_start_date: date | None = Field(None, examples=["2025-01-01"])
    actual_end_date: date | None = Field(None, examples=["2026-01-01"])
    planned_start_date: date | None = Field(None, examples=["2024-12-12"])
    planned_end_date: date | None = Field(None, examples=["2025-01-01"])
    investment: float = Field(default=0.0, ge=0, le=100, examples=[0])
    pre_design: float = Field(default=0.0, ge=0, le=100, examples=[20.2])
    design: float = Field(default=0.0, ge=0, le=100, examples=[40.3])
    construction: float = Field(default=0.0, ge=0, le=100, examples=[60.4])
    operation: float = Field(default=0.0, ge=0, le=100, examples=[80.5])
    decommission: float = Field(default=0.0, ge=0, le=100, examples=[100])
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project's phases additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )

    @classmethod
    def from_dto(cls, dto: ProjectPhasesDTO) -> "ProjectPhases":
        return cls(
            actual_start_date=dto.actual_start_date,
            actual_end_date=dto.actual_end_date,
            planned_start_date=dto.planned_start_date,
            planned_end_date=dto.planned_end_date,
            investment=dto.investment,
            pre_design=dto.pre_design,
            design=dto.design,
            construction=dto.construction,
            operation=dto.operation,
            decommission=dto.decommission,
            properties=dto.properties,
        )


class ProjectPhasesPut(BaseModel):
    """Project's phases PUT schema."""

    actual_start_date: date | None = Field(..., examples=["2025-01-01"])
    actual_end_date: date | None = Field(..., examples=["2026-01-01"])
    planned_start_date: date | None = Field(..., examples=["2024-12-12"])
    planned_end_date: date | None = Field(..., examples=["2025-01-01"])
    investment: float = Field(..., ge=0, le=100, examples=[0])
    pre_design: float = Field(..., ge=0, le=100, examples=[20.2])
    design: float = Field(..., ge=0, le=100, examples=[40.3])
    construction: float = Field(..., ge=0, le=100, examples=[60.4])
    operation: float = Field(..., ge=0, le=100, examples=[80.5])
    decommission: float = Field(..., ge=0, le=100, examples=[100])
    properties: dict[str, Any] = Field(
        ...,
        description="project's phases additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
