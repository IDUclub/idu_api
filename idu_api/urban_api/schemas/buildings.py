"""Living buildings schemas are defined here."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class BuildingPost(BaseModel):
    """Building schema for POST requests."""

    physical_object_id: int = Field(..., examples=[1])
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    floors: int | None = Field(None, examples=[1])
    building_area_official: float | None = Field(None, examples=[1.0])
    building_area_modeled: float | None = Field(None, examples=[1.0])
    project_type: str | None = Field(None, examples=["example"])
    floor_type: str | None = Field(None, examples=["example"])
    wall_material: str | None = Field(None, examples=["example"])
    built_year: int | None = Field(None, examples=[1])
    exploitation_start_year: int | None = Field(None, examples=[1])


class BuildingPut(BaseModel):
    """Building schema for PUT requests."""

    physical_object_id: int = Field(..., examples=[1])
    properties: dict[str, Any] = Field(
        ..., description="additional properties", examples=[{"additional_attribute_name": "additional_attribute_value"}]
    )
    floors: int | None = Field(..., examples=[1])
    building_area_official: float | None = Field(..., examples=[1.0])
    building_area_modeled: float | None = Field(..., examples=[1.0])
    project_type: str | None = Field(..., examples=["example"])
    floor_type: str | None = Field(..., examples=["example"])
    wall_material: str | None = Field(..., examples=["example"])
    built_year: int | None = Field(..., examples=[1])
    exploitation_start_year: int | None = Field(..., examples=[1])


class BuildingPatch(BaseModel):
    """Building schema for PATCH requests."""

    physical_object_id: int | None = Field(None, examples=[1])
    properties: dict[str, Any] | None = Field(
        None,
        description="additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    floors: int | None = Field(None, examples=[1])
    building_area_official: float | None = Field(None, examples=[1.0])
    building_area_modeled: float | None = Field(None, examples=[1.0])
    project_type: str | None = Field(None, examples=["example"])
    floor_type: str | None = Field(None, examples=["example"])
    wall_material: str | None = Field(None, examples=["example"])
    built_year: int | None = Field(None, examples=[1])
    exploitation_start_year: int | None = Field(None, examples=[1])

    @model_validator(mode="before")
    @classmethod
    def check_empty_request(cls, values):
        """Ensure the request body is not empty."""
        if not values:
            raise ValueError("request body cannot be empty")
        return values


class ScenarioBuildingPost(BuildingPost):
    """Building for scenario physical object schema for POST requests."""

    is_scenario_object: bool = Field(..., description="boolean parameter to determine scenario object")


class ScenarioBuildingPut(BuildingPut):
    """Building for scenario physical object schema for PUT requests."""

    is_scenario_object: bool = Field(..., description="boolean parameter to determine scenario object")


class ScenarioBuildingPatch(BaseModel):
    """Building for scenario physical object schema for PATCH requests."""

    properties: dict[str, Any] | None = Field(
        None,
        description="additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    floors: int | None = Field(None, examples=[1])
    building_area_official: float | None = Field(None, examples=[1.0])
    building_area_modeled: float | None = Field(None, examples=[1.0])
    project_type: str | None = Field(None, examples=["example"])
    floor_type: str | None = Field(None, examples=["example"])
    wall_material: str | None = Field(None, examples=["example"])
    built_year: int | None = Field(None, examples=[1])
    exploitation_start_year: int | None = Field(None, examples=[1])
