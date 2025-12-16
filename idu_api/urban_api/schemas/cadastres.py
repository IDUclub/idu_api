from typing import Any

from pydantic import BaseModel, Field

from idu_api.urban_api.schemas.geometries import GeometryValidationModel


class ProjectCadastreAttributes(BaseModel):
    """Projects cadastre schema with all attributes (without geometry columns)."""

    project_cadastre_id: int = Field(..., description="project cadastre identifier", examples=[1])
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional cadastre properties (JSONB)",
    )
    area: float | None = Field(None, examples=[1250.5])
    cad_num: str | None = Field(None, examples=["77:01:0004012:345"])
    cost_value: float | None = Field(None, examples=[1500000.0])
    land_record_area: float | None = Field(None, examples=[1200.0])
    land_record_category_type: str | None = Field(None, examples=["Земли населённых пунктов"])
    ownership_type: str | None = Field(None, examples=["Собственность"])
    permitted_use_established_by_document: str | None = Field(
        None,
        examples=["Для размещения объектов жилой застройки"],
    )
    quarter_cad_number: str | None = Field(None, examples=["77:01:0004012"])
    readable_address: str | None = Field(
        None,
        description="Human-readable address",
        examples=["г. Москва, ул. Тверская, д. 1"],
    )
    specified_area: float | None = Field(None, examples=[1230.0])
    status: str | None = Field(None, examples=["Учтён"])
    zone_pzz: str | None = Field(None, examples=["Ж-1"])
    possible_pzz_vri: str | None = Field(None, examples=["Жилая застройка"])
    possible_vri_list: str | None = Field(
        None,
        description="Possible permitted use list (raw text)",
    )
    similarity_score: float | None = Field(
        None,
        description="Similarity score between cadastre object and project territory",
        examples=[0.92],
    )


class ProjectCadastrePut(GeometryValidationModel):
    """Project cadastres schema for PUT request."""

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional cadastre properties (JSONB)",
    )
    area: float | None = Field(None, examples=[1250.5])
    cad_num: str | None = Field(None, examples=["77:01:0004012:345"])
    cost_value: float | None = Field(None, examples=[1500000.0])
    land_record_area: float | None = Field(None, examples=[1200.0])
    land_record_category_type: str | None = Field(None, examples=["Земли населённых пунктов"])
    ownership_type: str | None = Field(None, examples=["Собственность"])
    permitted_use_established_by_document: str | None = Field(
        None,
        examples=["Для размещения объектов жилой застройки"],
    )
    quarter_cad_number: str | None = Field(None, examples=["77:01:0004012"])
    readable_address: str | None = Field(
        None,
        description="Human-readable address",
        examples=["г. Москва, ул. Тверская, д. 1"],
    )
    specified_area: float | None = Field(None, examples=[1230.0])
    status: str | None = Field(None, examples=["Учтён"])
    zone_pzz: str | None = Field(None, examples=["Ж-1"])
    possible_pzz_vri: str | None = Field(None, examples=["Жилая застройка"])
    possible_vri_list: str | None = Field(
        None,
        description="Possible permitted use list (raw text)",
    )
    similarity_score: float | None = Field(
        None,
        description="Similarity score between cadastre object and project territory",
        examples=[0.92],
    )
