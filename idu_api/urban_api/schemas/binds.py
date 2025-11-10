"""Territory indicators bindings schemas are defined here."""

from pydantic import BaseModel, Field

from idu_api.urban_api.dto import ShortTerritoryIndicatorBindDTO, TerritoryIndicatorBindDTO
from idu_api.urban_api.schemas.short_models import MeasurementUnitBasic, ShortIndicatorInfo, ShortTerritory


class ShortTerritoryIndicatorBind(BaseModel):
    """Short territory indicators bindings schema with only important fields."""

    indicator_id: int = Field(..., description="indicator identifier", examples=[1])
    indicator_name: str = Field(..., description="indicator name", examples=["--"])
    measurement_unit_name: str | None = Field(..., description="measurement unit name", examples=["--"])
    min_value: float = Field(..., description="minimum binned value", examples=[0.0])
    max_value: float = Field(..., description="maximum binned value", examples=[100.0])

    @classmethod
    def from_dto(cls, dto: ShortTerritoryIndicatorBindDTO) -> "ShortTerritoryIndicatorBind":
        return cls(
            indicator_id=dto.indicator_id,
            indicator_name=dto.indicator_name,
            measurement_unit_name=dto.measurement_unit_name,
            min_value=dto.min_value,
            max_value=dto.max_value,
        )


class TerritoryIndicatorBind(BaseModel):
    """Territory indicators bindings schema with all attributes."""

    indicator: ShortIndicatorInfo
    region: ShortTerritory
    level: int = Field(..., description="territory level for which bindings were defined", examples=[3])
    min_value: float = Field(..., description="minimum binned value", examples=[0.0])
    max_value: float = Field(..., description="maximum binned value", examples=[100.0])

    @classmethod
    def from_dto(cls, dto: TerritoryIndicatorBindDTO) -> "TerritoryIndicatorBind":
        return cls(
            indicator=ShortIndicatorInfo(
                indicator_id=dto.indicator_id,
                name_full=dto.indicator_name,
                parent_id=dto.indicator_parent_id,
                list_label=dto.indicator_list_label,
                level=dto.indicator_level,
                measurement_unit=MeasurementUnitBasic(id=dto.measurement_unit_id, name=dto.measurement_unit_name),
            ),
            region=ShortTerritory(id=dto.territory_id, name=dto.territory_name),
            level=dto.territory_level,
            min_value=dto.min_value,
            max_value=dto.max_value,
        )


class TerritoryIndicatorBindPut(BaseModel):
    """Territory indicators bindings schema for POST requests."""

    indicator_id: int = Field(..., description="indicator identifier", examples=[1])
    territory_id: int = Field(..., description="regional (level=2) territory identifier", examples=[1])
    level: int = Field(..., description="territory level for which bindings are defined", examples=[3])
    min_value: float = Field(..., description="minimum binned value", examples=[0.0])
    max_value: float = Field(..., description="maximum binned value", examples=[100.0])
