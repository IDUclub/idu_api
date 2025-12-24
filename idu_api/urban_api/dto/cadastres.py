"""Projects cadastres DTOs are defined here."""

from dataclasses import asdict, dataclass
from typing import Any

import shapely.geometry as geom
from shapely.wkb import loads as wkb_loads


@dataclass
class ProjectCadastreDTO:  # pylint: disable=too-many-instance-attributes
    project_cadastre_id: int
    geometry: geom.Polygon | geom.MultiPolygon
    centre_point: geom.Point
    properties: dict[str, Any]
    area: float | None
    cad_num: str | None
    cost_value: float | None
    land_record_area: float | None
    land_record_category_type: str | None
    ownership_type: str | None
    permitted_use_established_by_document: str | None
    quarter_cad_number: str | None
    readable_address: str | None
    specified_area: float | None
    status: str | None
    zone_pzz: str | None
    possible_pzz_vri: str | None
    possible_vri_list: str | None
    similarity_score: float | None

    def __post_init__(self) -> None:
        if isinstance(self.centre_point, bytes):
            self.centre_point = wkb_loads(self.centre_point)
        if self.geometry is None:
            self.geometry = self.centre_point
        if isinstance(self.geometry, bytes):
            self.geometry = wkb_loads(self.geometry)

    def to_geojson_dict(self):
        return asdict(self)
