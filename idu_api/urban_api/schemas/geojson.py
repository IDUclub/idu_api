"""GeoJSON response models are defined here."""

from collections.abc import Iterable
from typing import Any, Literal

import shapely.geometry as geom
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel

from idu_api.urban_api.schemas.binds import ShortTerritoryIndicatorBind
from idu_api.urban_api.schemas.geometries import AllPossibleGeometry
from idu_api.urban_api.schemas.territories import TerritoryWithIndicators

_BaseGeomTypes = (
    geom.Point | geom.MultiPoint | geom.Polygon | geom.MultiPolygon | geom.LineString | geom.MultiLineString
)


class GeoJSONResponse(FeatureCollection):
    type: Literal["FeatureCollection"] = "FeatureCollection"

    @classmethod
    async def from_list(
        cls,
        features: Iterable[dict[str, Any]],
        centers_only: bool = False,
        save_centers: bool = False,
    ) -> "GeoJSONResponse":
        """
        Construct GeoJSON model from list of dictionaries,
        with one field in each containing GeoJSON geometries.
        """
        geom_columns = ("geometry", "centre_point") if not save_centers else "geometry"
        feature_collection = [
            Feature(
                type="Feature",
                geometry=feature["centre_point" if centers_only else "geometry"],
                properties={k: v for k, v in feature.items() if k not in geom_columns},
            )
            for feature in features
        ]
        return cls(features=feature_collection)

    def update_geometries(
        self, new_geoms: list[_BaseGeomTypes | geom.MultiPoint | geom.GeometryCollection]
    ) -> "GeoJSONResponse":
        """
        Updates the geometries in each Feature, accepting a list of new Shapely geometries.
        The number of new geometries must match the number of features.
        """
        if len(new_geoms) != len(self.features):
            raise ValueError(
                f"Number of new geometries ({len(new_geoms)}) does not match the number of features ({len(self.features)})"
            )

        updated_features = [
            feature.copy(update={"geometry": AllPossibleGeometry.from_shapely_geometry(new_geom)})
            for feature, new_geom in zip(self.features, new_geoms)
        ]

        return GeoJSONResponse(features=updated_features)


class TerritoriesWithBinnedIndicators(BaseModel):
    """Response model containing geojson with territory indicator values info
    in properties + binned values for indicators."""

    geojson: GeoJSONResponse[Feature[Geometry, TerritoryWithIndicators]]
    binned: list[ShortTerritoryIndicatorBind]
