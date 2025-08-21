"""Unit tests for scenario physical objects are defined here."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from geoalchemy2.functions import (
    ST_AsEWKB,
    ST_Centroid,
    ST_GeomFromWKB,
    ST_Intersection,
    ST_Intersects,
    ST_IsEmpty,
    ST_Within,
)
from sqlalchemy import ScalarSelect, delete, insert, literal, or_, select, text, union_all, update
from sqlalchemy.sql.functions import coalesce

from idu_api.common.db.entities import (
    buildings_data,
    object_geometries_data,
    physical_object_functions_dict,
    physical_object_types_dict,
    physical_objects_data,
    projects_buildings_data,
    projects_object_geometries_data,
    projects_physical_objects_data,
    projects_territory_data,
    projects_urban_objects_data,
    territories_data,
    urban_objects_data,
)
from idu_api.urban_api.dto import (
    ScenarioPhysicalObjectDTO,
    ScenarioPhysicalObjectWithGeometryDTO,
    ScenarioUrbanObjectDTO,
    UserDTO,
)
from idu_api.urban_api.exceptions.logic.common import EntityAlreadyExists, EntityNotFoundById
from idu_api.urban_api.logic.impl.helpers.projects_physical_objects import (
    add_building_to_db,
    add_physical_object_with_geometry_to_db,
    delete_building_from_db,
    delete_physical_object_from_db,
    get_context_physical_objects_from_db,
    get_context_physical_objects_with_geometry_from_db,
    get_physical_objects_by_scenario_id_from_db,
    get_physical_objects_with_geometry_by_scenario_id_from_db,
    get_scenario_physical_object_by_id_from_db,
    patch_building_to_db,
    patch_physical_object_to_db,
    put_building_to_db,
    put_physical_object_to_db,
    update_physical_objects_by_function_id_to_db,
)
from idu_api.urban_api.logic.impl.helpers.utils import SRID, include_child_territories_cte
from idu_api.urban_api.schemas import (
    PhysicalObject,
    PhysicalObjectPatch,
    PhysicalObjectPut,
    PhysicalObjectWithGeometryPost,
    ScenarioBuildingPatch,
    ScenarioBuildingPost,
    ScenarioBuildingPut,
    ScenarioPhysicalObject,
    ScenarioPhysicalObjectWithGeometryAttributes,
    ScenarioUrbanObject,
)
from idu_api.urban_api.schemas.geometries import GeoJSONResponse
from tests.urban_api.helpers.connection import MockConnection

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
async def test_get_physical_objects_by_scenario_id_from_db(mock_conn: MockConnection):
    """Test the get_physical_objects_by_scenario_id_from_db function."""

    # Arrange
    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_type_id = 1
    physical_object_function_id = None
    building_columns = [col for col in buildings_data.c if col.name not in ("physical_object_id", "properties")]

    territories_cte = include_child_territories_cte(1)
    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id)
        .where(projects_urban_objects_data.c.scenario_id == scenario_id)
        .where(projects_urban_objects_data.c.public_urban_object_id.isnot(None))
    ).cte(name="public_urban_object_ids")

    public_urban_objects_query = (
        select(
            physical_objects_data.c.physical_object_id,
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            physical_objects_data.c.name,
            physical_objects_data.c.properties,
            physical_objects_data.c.created_at,
            physical_objects_data.c.updated_at,
            *building_columns,
            buildings_data.c.properties.label("building_properties"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            literal(False).label("is_scenario_object"),
        )
        .select_from(
            urban_objects_data.join(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == urban_objects_data.c.physical_object_id,
            )
            .join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
            .join(
                territories_data,
                territories_data.c.territory_id == object_geometries_data.c.territory_id,
            )
            .join(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id == physical_objects_data.c.physical_object_type_id,
            )
            .join(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids)),
            True,
            object_geometries_data.c.territory_id.in_(select(territories_cte.c.territory_id)),
        )
        .distinct()
    )

    scenario_urban_objects_query = (
        select(
            coalesce(
                projects_physical_objects_data.c.physical_object_id,
                physical_objects_data.c.physical_object_id,
            ).label("physical_object_id"),
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            coalesce(
                projects_physical_objects_data.c.name,
                physical_objects_data.c.name,
            ).label("name"),
            coalesce(
                projects_physical_objects_data.c.properties,
                physical_objects_data.c.properties,
            ).label("properties"),
            coalesce(
                projects_physical_objects_data.c.created_at,
                physical_objects_data.c.created_at,
            ).label("created_at"),
            coalesce(
                projects_physical_objects_data.c.updated_at,
                physical_objects_data.c.updated_at,
            ).label("updated_at"),
            coalesce(
                projects_buildings_data.c.building_id,
                buildings_data.c.building_id,
            ).label("building_id"),
            coalesce(
                projects_buildings_data.c.floors,
                buildings_data.c.floors,
            ).label("floors"),
            coalesce(
                projects_buildings_data.c.building_area_official,
                buildings_data.c.building_area_official,
            ).label("building_area_official"),
            coalesce(
                projects_buildings_data.c.building_area_modeled,
                buildings_data.c.building_area_modeled,
            ).label("building_area_modeled"),
            coalesce(
                projects_buildings_data.c.project_type,
                buildings_data.c.project_type,
            ).label("project_type"),
            coalesce(
                projects_buildings_data.c.floor_type,
                buildings_data.c.floor_type,
            ).label("floor_type"),
            coalesce(
                projects_buildings_data.c.wall_material,
                buildings_data.c.wall_material,
            ).label("wall_material"),
            coalesce(
                projects_buildings_data.c.built_year,
                buildings_data.c.built_year,
            ).label("built_year"),
            coalesce(
                projects_buildings_data.c.exploitation_start_year,
                buildings_data.c.exploitation_start_year,
            ).label("exploitation_start_year"),
            coalesce(
                projects_buildings_data.c.properties,
                buildings_data.c.properties,
            ).label("building_properties"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            (projects_urban_objects_data.c.physical_object_id.isnot(None)).label("is_scenario_object"),
        )
        .select_from(
            projects_urban_objects_data.outerjoin(
                projects_physical_objects_data,
                projects_physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.public_physical_object_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
            .outerjoin(
                territories_data,
                or_(
                    territories_data.c.territory_id == projects_object_geometries_data.c.territory_id,
                    territories_data.c.territory_id == object_geometries_data.c.territory_id,
                ),
            )
            .outerjoin(
                physical_object_types_dict,
                or_(
                    physical_object_types_dict.c.physical_object_type_id
                    == projects_physical_objects_data.c.physical_object_type_id,
                    physical_object_types_dict.c.physical_object_type_id
                    == physical_objects_data.c.physical_object_type_id,
                ),
            )
            .outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_buildings_data,
                projects_buildings_data.c.physical_object_id == projects_physical_objects_data.c.physical_object_id,
            )
        )
        .where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.is_(None),
        )
        .distinct()
    )
    union_query = union_all(public_urban_objects_query, scenario_urban_objects_query).cte(name="union_query")
    statement = select(union_query).where(union_query.c.physical_object_type_id == physical_object_type_id)

    # Act
    result = await get_physical_objects_by_scenario_id_from_db(
        mock_conn, scenario_id, user, physical_object_type_id, physical_object_function_id
    )

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, ScenarioPhysicalObjectDTO) for item in result
    ), "Each item should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result[0]), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_physical_objects_with_geometry_by_scenario_id_from_db(mock_conn: MockConnection):
    """Test the get_physical_objects_with_geometry_by_scenario_id_from_db function."""

    # Arrange
    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_type_id = 1
    physical_object_function_id = None
    building_columns = [col for col in buildings_data.c if col.name not in ("physical_object_id", "properties")]

    territories_cte = include_child_territories_cte(1)
    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id)
        .where(projects_urban_objects_data.c.scenario_id == scenario_id)
        .where(projects_urban_objects_data.c.public_urban_object_id.isnot(None))
    ).cte(name="public_urban_object_ids")

    public_urban_objects_query = (
        select(
            physical_objects_data.c.physical_object_id,
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            physical_objects_data.c.name,
            physical_objects_data.c.properties,
            physical_objects_data.c.created_at,
            physical_objects_data.c.updated_at,
            *building_columns,
            buildings_data.c.properties.label("building_properties"),
            object_geometries_data.c.object_geometry_id,
            object_geometries_data.c.address,
            object_geometries_data.c.osm_id,
            ST_AsEWKB(object_geometries_data.c.geometry).label("geometry"),
            ST_AsEWKB(object_geometries_data.c.centre_point).label("centre_point"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            literal(False).label("is_scenario_physical_object"),
            literal(False).label("is_scenario_geometry"),
        )
        .select_from(
            urban_objects_data.join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
            .join(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == urban_objects_data.c.physical_object_id,
            )
            .join(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id == physical_objects_data.c.physical_object_type_id,
            )
            .join(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
            .join(
                territories_data,
                territories_data.c.territory_id == object_geometries_data.c.territory_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids)),
            True,
            object_geometries_data.c.territory_id.in_(select(territories_cte.c.territory_id)),
        )
    )

    scenario_urban_objects_query = (
        select(
            coalesce(
                projects_physical_objects_data.c.physical_object_id,
                physical_objects_data.c.physical_object_id,
            ).label("physical_object_id"),
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            coalesce(
                projects_physical_objects_data.c.name,
                physical_objects_data.c.name,
            ).label("name"),
            coalesce(
                projects_physical_objects_data.c.properties,
                physical_objects_data.c.properties,
            ).label("properties"),
            coalesce(
                projects_physical_objects_data.c.created_at,
                physical_objects_data.c.created_at,
            ).label("created_at"),
            coalesce(
                projects_physical_objects_data.c.updated_at,
                physical_objects_data.c.updated_at,
            ).label("updated_at"),
            coalesce(
                projects_buildings_data.c.building_id,
                buildings_data.c.building_id,
            ).label("building_id"),
            coalesce(
                projects_buildings_data.c.floors,
                buildings_data.c.floors,
            ).label("floors"),
            coalesce(
                projects_buildings_data.c.building_area_official,
                buildings_data.c.building_area_official,
            ).label("building_area_official"),
            coalesce(
                projects_buildings_data.c.building_area_modeled,
                buildings_data.c.building_area_modeled,
            ).label("building_area_modeled"),
            coalesce(
                projects_buildings_data.c.project_type,
                buildings_data.c.project_type,
            ).label("project_type"),
            coalesce(
                projects_buildings_data.c.floor_type,
                buildings_data.c.floor_type,
            ).label("floor_type"),
            coalesce(
                projects_buildings_data.c.wall_material,
                buildings_data.c.wall_material,
            ).label("wall_material"),
            coalesce(
                projects_buildings_data.c.built_year,
                buildings_data.c.built_year,
            ).label("built_year"),
            coalesce(
                projects_buildings_data.c.exploitation_start_year,
                buildings_data.c.exploitation_start_year,
            ).label("exploitation_start_year"),
            coalesce(
                projects_buildings_data.c.properties,
                buildings_data.c.properties,
            ).label("building_properties"),
            coalesce(
                projects_object_geometries_data.c.object_geometry_id,
                object_geometries_data.c.object_geometry_id,
            ).label("object_geometry_id"),
            coalesce(
                projects_object_geometries_data.c.address,
                object_geometries_data.c.address,
            ).label("address"),
            coalesce(
                projects_object_geometries_data.c.osm_id,
                object_geometries_data.c.osm_id,
            ).label("osm_id"),
            coalesce(
                projects_object_geometries_data.c.geometry,
                object_geometries_data.c.geometry,
            ).label("geometry"),
            coalesce(
                projects_object_geometries_data.c.centre_point,
                object_geometries_data.c.centre_point,
            ).label("centre_point"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            (projects_urban_objects_data.c.physical_object_id.isnot(None)).label("is_scenario_physical_object"),
            (projects_urban_objects_data.c.object_geometry_id.isnot(None)).label("is_scenario_geometry"),
        )
        .select_from(
            projects_urban_objects_data.outerjoin(
                projects_physical_objects_data,
                projects_physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.public_physical_object_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
            .outerjoin(
                physical_object_types_dict,
                or_(
                    physical_object_types_dict.c.physical_object_type_id
                    == projects_physical_objects_data.c.physical_object_type_id,
                    physical_object_types_dict.c.physical_object_type_id
                    == physical_objects_data.c.physical_object_type_id,
                ),
            )
            .outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                territories_data,
                or_(
                    territories_data.c.territory_id == projects_object_geometries_data.c.territory_id,
                    territories_data.c.territory_id == object_geometries_data.c.territory_id,
                ),
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_buildings_data,
                projects_buildings_data.c.physical_object_id == projects_physical_objects_data.c.physical_object_id,
            )
        )
        .where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.is_(None),
        )
    )
    union_query = union_all(public_urban_objects_query, scenario_urban_objects_query).cte(name="union_query")
    statement = select(union_query).where(union_query.c.physical_object_type_id == physical_object_type_id)

    # Act
    result = await get_physical_objects_with_geometry_by_scenario_id_from_db(
        mock_conn, scenario_id, user, physical_object_type_id, physical_object_function_id
    )
    geojson_result = await GeoJSONResponse.from_list([r.to_geojson_dict() for r in result])

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, ScenarioPhysicalObjectWithGeometryDTO) for item in result
    ), "Each item should be a ScenarioPhysicalObjectWithGeometryDTO."
    assert isinstance(
        ScenarioPhysicalObjectWithGeometryAttributes(**geojson_result.features[0].properties),
        ScenarioPhysicalObjectWithGeometryAttributes,
    ), "Couldn't create pydantic model from geojson properties."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_context_physical_objects_from_db(mock_conn: MockConnection):
    """Test the get_context_physical_objects_from_db function."""

    # Arrange
    project_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_type_id = 1
    physical_object_function_id = None
    mock_geom = str(MagicMock(spec=ScalarSelect))

    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id)
        .where(projects_urban_objects_data.c.scenario_id == 1)
        .where(projects_urban_objects_data.c.public_urban_object_id.isnot(None))
    ).cte(name="public_urban_object_ids")
    objects_intersecting = (
        select(object_geometries_data.c.object_geometry_id)
        .select_from(
            object_geometries_data.join(
                urban_objects_data,
                urban_objects_data.c.object_geometry_id == object_geometries_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids)),
            object_geometries_data.c.territory_id.in_([1])
            | ST_Intersects(object_geometries_data.c.geometry, mock_geom),
        )
        .cte(name="objects_intersecting")
    )
    building_columns = [col for col in buildings_data.c if col.name not in ("physical_object_id", "properties")]
    public_urban_objects_query = select(
        physical_objects_data.c.physical_object_id,
        physical_object_types_dict.c.physical_object_type_id,
        physical_object_types_dict.c.name.label("physical_object_type_name"),
        physical_object_functions_dict.c.physical_object_function_id,
        physical_object_functions_dict.c.name.label("physical_object_function_name"),
        physical_objects_data.c.name,
        physical_objects_data.c.properties,
        physical_objects_data.c.created_at,
        physical_objects_data.c.updated_at,
        *building_columns,
        buildings_data.c.properties.label("building_properties"),
        territories_data.c.territory_id,
        territories_data.c.name.label("territory_name"),
        literal(False).label("is_scenario_object"),
    ).select_from(
        urban_objects_data.join(
            physical_objects_data,
            physical_objects_data.c.physical_object_id == urban_objects_data.c.physical_object_id,
        )
        .join(
            object_geometries_data,
            object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
        )
        .join(
            objects_intersecting,
            objects_intersecting.c.object_geometry_id == object_geometries_data.c.object_geometry_id,
        )
        .join(
            territories_data,
            territories_data.c.territory_id == object_geometries_data.c.territory_id,
        )
        .join(
            physical_object_types_dict,
            physical_object_types_dict.c.physical_object_type_id == physical_objects_data.c.physical_object_type_id,
        )
        .join(
            physical_object_functions_dict,
            physical_object_functions_dict.c.physical_object_function_id
            == physical_object_types_dict.c.physical_object_function_id,
        )
        .outerjoin(
            buildings_data,
            buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
        )
    )

    scenario_urban_objects_query = (
        select(
            coalesce(
                projects_physical_objects_data.c.physical_object_id,
                physical_objects_data.c.physical_object_id,
            ).label("physical_object_id"),
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            coalesce(
                projects_physical_objects_data.c.name,
                physical_objects_data.c.name,
            ).label("name"),
            coalesce(
                projects_physical_objects_data.c.properties,
                physical_objects_data.c.properties,
            ).label("properties"),
            coalesce(
                projects_physical_objects_data.c.created_at,
                physical_objects_data.c.created_at,
            ).label("created_at"),
            coalesce(
                projects_physical_objects_data.c.updated_at,
                physical_objects_data.c.updated_at,
            ).label("updated_at"),
            coalesce(
                projects_buildings_data.c.building_id,
                buildings_data.c.building_id,
            ).label("building_id"),
            coalesce(
                projects_buildings_data.c.floors,
                buildings_data.c.floors,
            ).label("floors"),
            coalesce(
                projects_buildings_data.c.building_area_official,
                buildings_data.c.building_area_official,
            ).label("building_area_official"),
            coalesce(
                projects_buildings_data.c.building_area_modeled,
                buildings_data.c.building_area_modeled,
            ).label("building_area_modeled"),
            coalesce(
                projects_buildings_data.c.project_type,
                buildings_data.c.project_type,
            ).label("project_type"),
            coalesce(
                projects_buildings_data.c.floor_type,
                buildings_data.c.floor_type,
            ).label("floor_type"),
            coalesce(
                projects_buildings_data.c.wall_material,
                buildings_data.c.wall_material,
            ).label("wall_material"),
            coalesce(
                projects_buildings_data.c.built_year,
                buildings_data.c.built_year,
            ).label("built_year"),
            coalesce(
                projects_buildings_data.c.exploitation_start_year,
                buildings_data.c.exploitation_start_year,
            ).label("exploitation_start_year"),
            coalesce(
                projects_buildings_data.c.properties,
                buildings_data.c.properties,
            ).label("building_properties"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            (projects_urban_objects_data.c.physical_object_id.isnot(None)).label("is_scenario_object"),
        )
        .select_from(
            projects_urban_objects_data.outerjoin(
                projects_physical_objects_data,
                projects_physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.public_physical_object_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
            .outerjoin(
                territories_data,
                or_(
                    territories_data.c.territory_id == projects_object_geometries_data.c.territory_id,
                    territories_data.c.territory_id == object_geometries_data.c.territory_id,
                ),
            )
            .outerjoin(
                physical_object_types_dict,
                or_(
                    physical_object_types_dict.c.physical_object_type_id
                    == projects_physical_objects_data.c.physical_object_type_id,
                    physical_object_types_dict.c.physical_object_type_id
                    == physical_objects_data.c.physical_object_type_id,
                ),
            )
            .outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_buildings_data,
                projects_buildings_data.c.physical_object_id == projects_physical_objects_data.c.physical_object_id,
            )
        )
        .where(
            projects_urban_objects_data.c.scenario_id == 1,
            projects_urban_objects_data.c.public_urban_object_id.is_(None),
        )
        .distinct()
    )
    union_query = union_all(public_urban_objects_query, scenario_urban_objects_query).cte(name="union_query")
    statement = select(union_query).where(union_query.c.physical_object_type_id == physical_object_type_id)

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.get_context_territories_geometry",
        new_callable=AsyncMock,
    ) as mock_get_context:
        mock_get_context.return_value = 1, mock_geom, [1]
        result = await get_context_physical_objects_from_db(
            mock_conn, project_id, user, physical_object_type_id, physical_object_function_id
        )

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, ScenarioPhysicalObjectDTO) for item in result
    ), "Each item should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result[0]), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_context_physical_objects_with_geometry_from_db(mock_conn: MockConnection):
    """Test the get_context_physical_objects_with_geometry_from_db function."""

    # Arrange
    project_id = 1
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_type_id = 1
    physical_object_function_id = None
    mock_geom = str(MagicMock(spec=ScalarSelect))

    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id)
        .where(projects_urban_objects_data.c.scenario_id == 1)
        .where(projects_urban_objects_data.c.public_urban_object_id.isnot(None))
    ).cte(name="public_urban_object_ids")
    objects_intersecting = (
        select(object_geometries_data.c.object_geometry_id)
        .select_from(
            object_geometries_data.join(
                urban_objects_data,
                urban_objects_data.c.object_geometry_id == object_geometries_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids)),
            object_geometries_data.c.territory_id.in_([1])
            | ST_Intersects(object_geometries_data.c.geometry, mock_geom),
        )
        .cte(name="objects_intersecting")
    )
    building_columns = [col for col in buildings_data.c if col.name not in ("physical_object_id", "properties")]
    intersected_geom = ST_Intersection(object_geometries_data.c.geometry, mock_geom)
    public_urban_objects_query = (
        select(
            physical_objects_data.c.physical_object_id,
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            physical_objects_data.c.name,
            physical_objects_data.c.properties,
            physical_objects_data.c.created_at,
            physical_objects_data.c.updated_at,
            *building_columns,
            buildings_data.c.properties.label("building_properties"),
            object_geometries_data.c.object_geometry_id,
            object_geometries_data.c.address,
            object_geometries_data.c.osm_id,
            ST_AsEWKB(intersected_geom).label("geometry"),
            ST_AsEWKB(ST_Centroid(intersected_geom)).label("centre_point"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            literal(False).label("is_scenario_physical_object"),
            literal(False).label("is_scenario_geometry"),
        )
        .select_from(
            urban_objects_data.join(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == urban_objects_data.c.physical_object_id,
            )
            .join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
            .join(
                objects_intersecting,
                objects_intersecting.c.object_geometry_id == object_geometries_data.c.object_geometry_id,
            )
            .join(
                territories_data,
                territories_data.c.territory_id == object_geometries_data.c.territory_id,
            )
            .join(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id == physical_objects_data.c.physical_object_type_id,
            )
            .join(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
        )
        .where(~ST_IsEmpty(intersected_geom))
        .distinct()
    )
    geom_expr = ST_Intersection(
        coalesce(
            projects_object_geometries_data.c.geometry,
            object_geometries_data.c.geometry,
        ),
        mock_geom,
    )
    scenario_urban_objects_query = (
        select(
            coalesce(
                projects_physical_objects_data.c.physical_object_id,
                physical_objects_data.c.physical_object_id,
            ).label("physical_object_id"),
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            coalesce(
                projects_physical_objects_data.c.name,
                physical_objects_data.c.name,
            ).label("name"),
            coalesce(
                projects_physical_objects_data.c.properties,
                physical_objects_data.c.properties,
            ).label("properties"),
            coalesce(
                projects_physical_objects_data.c.created_at,
                physical_objects_data.c.created_at,
            ).label("created_at"),
            coalesce(
                projects_physical_objects_data.c.updated_at,
                physical_objects_data.c.updated_at,
            ).label("updated_at"),
            coalesce(
                projects_buildings_data.c.building_id,
                buildings_data.c.building_id,
            ).label("building_id"),
            coalesce(
                projects_buildings_data.c.floors,
                buildings_data.c.floors,
            ).label("floors"),
            coalesce(
                projects_buildings_data.c.building_area_official,
                buildings_data.c.building_area_official,
            ).label("building_area_official"),
            coalesce(
                projects_buildings_data.c.building_area_modeled,
                buildings_data.c.building_area_modeled,
            ).label("building_area_modeled"),
            coalesce(
                projects_buildings_data.c.project_type,
                buildings_data.c.project_type,
            ).label("project_type"),
            coalesce(
                projects_buildings_data.c.floor_type,
                buildings_data.c.floor_type,
            ).label("floor_type"),
            coalesce(
                projects_buildings_data.c.wall_material,
                buildings_data.c.wall_material,
            ).label("wall_material"),
            coalesce(
                projects_buildings_data.c.built_year,
                buildings_data.c.built_year,
            ).label("built_year"),
            coalesce(
                projects_buildings_data.c.exploitation_start_year,
                buildings_data.c.exploitation_start_year,
            ).label("exploitation_start_year"),
            coalesce(
                projects_buildings_data.c.properties,
                buildings_data.c.properties,
            ).label("building_properties"),
            coalesce(
                projects_object_geometries_data.c.object_geometry_id,
                object_geometries_data.c.object_geometry_id,
            ).label("object_geometry_id"),
            coalesce(
                projects_object_geometries_data.c.address,
                object_geometries_data.c.address,
            ).label("address"),
            coalesce(
                projects_object_geometries_data.c.osm_id,
                object_geometries_data.c.osm_id,
            ).label("osm_id"),
            ST_AsEWKB(geom_expr).label("geometry"),
            ST_AsEWKB(ST_Centroid(geom_expr)).label("centre_point"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
            (projects_urban_objects_data.c.physical_object_id.isnot(None)).label("is_scenario_physical_object"),
            (projects_urban_objects_data.c.object_geometry_id.isnot(None)).label("is_scenario_geometry"),
        )
        .select_from(
            projects_urban_objects_data.outerjoin(
                projects_physical_objects_data,
                projects_physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.public_physical_object_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
            .outerjoin(
                territories_data,
                or_(
                    territories_data.c.territory_id == projects_object_geometries_data.c.territory_id,
                    territories_data.c.territory_id == object_geometries_data.c.territory_id,
                ),
            )
            .outerjoin(
                physical_object_types_dict,
                or_(
                    physical_object_types_dict.c.physical_object_type_id
                    == projects_physical_objects_data.c.physical_object_type_id,
                    physical_object_types_dict.c.physical_object_type_id
                    == physical_objects_data.c.physical_object_type_id,
                ),
            )
            .outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                buildings_data,
                buildings_data.c.physical_object_id == physical_objects_data.c.physical_object_id,
            )
            .outerjoin(
                projects_buildings_data,
                projects_buildings_data.c.physical_object_id == projects_physical_objects_data.c.physical_object_id,
            )
        )
        .where(
            projects_urban_objects_data.c.scenario_id == 1,
            projects_urban_objects_data.c.public_urban_object_id.is_(None),
            ~ST_IsEmpty(geom_expr),
        )
        .distinct()
    )
    union_query = union_all(public_urban_objects_query, scenario_urban_objects_query).cte(name="union_query")
    statement = select(union_query).where(union_query.c.physical_object_type_id == physical_object_type_id)

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.get_context_territories_geometry",
        new_callable=AsyncMock,
    ) as mock_get_context:
        mock_get_context.return_value = 1, mock_geom, [1]
        result = await get_context_physical_objects_with_geometry_from_db(
            mock_conn, project_id, user, physical_object_type_id, physical_object_function_id
        )
    geojson_result = await GeoJSONResponse.from_list([r.to_geojson_dict() for r in result])

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, ScenarioPhysicalObjectWithGeometryDTO) for item in result
    ), "Each item should be a ScenarioPhysicalObjectWithGeometryDTO."
    assert isinstance(
        ScenarioPhysicalObjectWithGeometryAttributes(**geojson_result.features[0].properties),
        ScenarioPhysicalObjectWithGeometryAttributes,
    ), "Couldn't create pydantic model from geojson properties."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_scenario_physical_object_by_id_from_db(mock_conn: MockConnection):
    """Test the get_scenario_object_geometry_by_id_from_db function."""

    # Arrange
    physical_object_id = 1
    project_building_columns = [
        col for col in projects_buildings_data.c if col.name not in ("physical_object_id", "properties")
    ]
    statement = (
        select(
            projects_physical_objects_data.c.physical_object_id,
            physical_object_types_dict.c.physical_object_type_id,
            physical_object_types_dict.c.name.label("physical_object_type_name"),
            physical_object_functions_dict.c.physical_object_function_id,
            physical_object_functions_dict.c.name.label("physical_object_function_name"),
            projects_physical_objects_data.c.name,
            projects_physical_objects_data.c.properties,
            projects_physical_objects_data.c.created_at,
            projects_physical_objects_data.c.updated_at,
            literal(True).label("is_scenario_object"),
            *project_building_columns,
            projects_buildings_data.c.properties.label("building_properties"),
            territories_data.c.territory_id,
            territories_data.c.name.label("territory_name"),
        )
        .select_from(
            projects_urban_objects_data.join(
                projects_physical_objects_data,
                projects_physical_objects_data.c.physical_object_id == projects_urban_objects_data.c.physical_object_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                territories_data,
                or_(
                    territories_data.c.territory_id == projects_object_geometries_data.c.territory_id,
                    territories_data.c.territory_id == object_geometries_data.c.territory_id,
                ),
            )
            .outerjoin(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id
                == projects_physical_objects_data.c.physical_object_type_id,
            )
            .outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
            .outerjoin(
                projects_buildings_data,
                projects_buildings_data.c.physical_object_id == projects_physical_objects_data.c.physical_object_id,
            )
        )
        .where(projects_physical_objects_data.c.physical_object_id == physical_object_id)
        .distinct()
    )

    # Act
    result = await get_scenario_physical_object_by_id_from_db(mock_conn, physical_object_id)

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_called_once_with(str(statement))


@pytest.mark.asyncio
@patch("idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_scenario")
async def test_add_physical_object_with_geometry_to_db(
    mock_check: AsyncMock,
    mock_conn: MockConnection,
    physical_object_with_geometry_post_req: PhysicalObjectWithGeometryPost,
):
    """Test the add_physical_object_with_geometry_to_db function."""

    # Arrange
    async def check_territory(conn, table, conditions):
        if table == territories_data:
            return False
        return True

    async def check_physical_object_type(conn, table, conditions):
        if table == physical_object_types_dict:
            return False
        return True

    scenario_id = 1
    physical_object_id, object_geometry_id = 1, 1
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_statement = (
        insert(projects_physical_objects_data)
        .values(
            public_physical_object_id=None,
            physical_object_type_id=physical_object_with_geometry_post_req.physical_object_type_id,
            name=physical_object_with_geometry_post_req.name,
            properties=physical_object_with_geometry_post_req.properties,
        )
        .returning(projects_physical_objects_data.c.physical_object_id)
    )
    geometry_statement = (
        insert(projects_object_geometries_data)
        .values(
            public_object_geometry_id=None,
            territory_id=physical_object_with_geometry_post_req.territory_id,
            geometry=ST_GeomFromWKB(
                physical_object_with_geometry_post_req.geometry.as_shapely_geometry().wkb, text(str(SRID))
            ),
            centre_point=ST_GeomFromWKB(
                physical_object_with_geometry_post_req.centre_point.as_shapely_geometry().wkb, text(str(SRID))
            ),
            address=physical_object_with_geometry_post_req.address,
            osm_id=physical_object_with_geometry_post_req.osm_id,
        )
        .returning(projects_object_geometries_data.c.object_geometry_id)
    )
    urban_object_statement = (
        insert(projects_urban_objects_data)
        .values(scenario_id=scenario_id, physical_object_id=physical_object_id, object_geometry_id=object_geometry_id)
        .returning(urban_objects_data.c.urban_object_id)
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_territory),
    ):
        with pytest.raises(EntityNotFoundById):
            await add_physical_object_with_geometry_to_db(
                mock_conn, physical_object_with_geometry_post_req, scenario_id, user
            )
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object_type),
    ):
        with pytest.raises(EntityNotFoundById):
            await add_physical_object_with_geometry_to_db(
                mock_conn, physical_object_with_geometry_post_req, scenario_id, user
            )
    result = await add_physical_object_with_geometry_to_db(
        mock_conn, physical_object_with_geometry_post_req, scenario_id, user
    )

    # Assert
    assert isinstance(result, ScenarioUrbanObjectDTO), "Result should be a ScenarioUrbanObjectDTO."
    assert isinstance(
        ScenarioUrbanObject.from_dto(result), ScenarioUrbanObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(physical_object_statement))
    mock_conn.execute_mock.assert_any_call(str(geometry_statement))
    mock_conn.execute_mock.assert_any_call(str(urban_object_statement))
    mock_conn.commit_mock.assert_called_once()
    mock_check.assert_any_call(mock_conn, scenario_id, user, to_edit=True)


@pytest.mark.asyncio
async def test_put_scenario_physical_object_to_db(
    mock_conn: MockConnection, physical_object_put_req: PhysicalObjectPut
):
    """Test the put_physical_object_to_db function."""

    # Arrange
    async def check_physical_object(conn, table, conditions):
        if table == projects_physical_objects_data:
            return False
        return True

    async def check_physical_object_type(conn, table, conditions):
        if table == physical_object_types_dict:
            return False
        return True

    scenario_id = 1
    physical_object_id = 1
    is_scenario_object = True
    user = UserDTO(id="mock_string", is_superuser=False)
    update_statement = (
        update(projects_physical_objects_data)
        .where(projects_physical_objects_data.c.physical_object_id == physical_object_id)
        .values(**physical_object_put_req.model_dump(), updated_at=datetime.now(timezone.utc))
        .returning(projects_physical_objects_data.c.physical_object_id)
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object),
    ):
        with pytest.raises(EntityNotFoundById):
            await put_physical_object_to_db(
                mock_conn, physical_object_put_req, scenario_id, physical_object_id, is_scenario_object, user
            )
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object_type),
    ):
        with pytest.raises(EntityNotFoundById):
            await put_physical_object_to_db(
                mock_conn, physical_object_put_req, scenario_id, physical_object_id, is_scenario_object, user
            )
    result = await put_physical_object_to_db(
        mock_conn, physical_object_put_req, scenario_id, physical_object_id, is_scenario_object, user
    )

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(update_statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_patch_scenario_physical_object_to_db(
    mock_conn: MockConnection, physical_object_patch_req: PhysicalObjectPatch
):
    """Test the patch_physical_object_to_db function."""

    # Arrange
    async def check_physical_object_type(conn, table, conditions):
        if table == physical_object_types_dict:
            return False
        return True

    scenario_id = 1
    physical_object_id = 1
    is_scenario_object = True
    user = UserDTO(id="mock_string", is_superuser=False)
    update_statement = (
        update(projects_physical_objects_data)
        .where(projects_physical_objects_data.c.physical_object_id == physical_object_id)
        .values(**physical_object_patch_req.model_dump(exclude_unset=True), updated_at=datetime.now(timezone.utc))
        .returning(projects_physical_objects_data.c.physical_object_id)
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object_type),
    ):
        with pytest.raises(EntityNotFoundById):
            await patch_physical_object_to_db(
                mock_conn, physical_object_patch_req, scenario_id, physical_object_id, is_scenario_object, user
            )
    result = await patch_physical_object_to_db(
        mock_conn, physical_object_patch_req, scenario_id, physical_object_id, is_scenario_object, user
    )

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(update_statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_public_physical_object_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_from_db function."""

    # Arrange
    scenario_id = 1
    physical_object_id = 1
    is_scenario_object = False
    user = UserDTO(id="mock_string", is_superuser=False)
    delete_statement = delete(projects_urban_objects_data).where(
        projects_urban_objects_data.c.public_physical_object_id == physical_object_id
    )
    territories_cte = include_child_territories_cte(1)
    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id.label("urban_object_id"))
        .where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.is_not(None),
        )
        .cte(name="public_urban_object_ids")
    )
    select_urban_object_statement = (
        select(urban_objects_data)
        .select_from(
            urban_objects_data.join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.physical_object_id == physical_object_id,
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids.c.urban_object_id)),
            True,
            object_geometries_data.c.territory_id.in_(select(territories_cte.c.territory_id)),
        )
    )
    insert_public_urban_objects_statement = insert(projects_urban_objects_data).values(
        [{"public_urban_object_id": 1, "scenario_id": scenario_id}]
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence"
    ) as mock_check_existence:
        result = await delete_physical_object_from_db(
            mock_conn, scenario_id, physical_object_id, is_scenario_object, user
        )
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await delete_physical_object_from_db(mock_conn, scenario_id, physical_object_id, is_scenario_object, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_any_call(str(delete_statement))
    mock_conn.execute_mock.assert_any_call(str(select_urban_object_statement))
    mock_conn.execute_mock.assert_any_call(str(insert_public_urban_objects_statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_scenario_physical_object_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_from_db function."""

    # Arrange
    scenario_id = 1
    physical_object_id = 1
    is_scenario_object = True
    user = UserDTO(id="mock_string", is_superuser=False)
    delete_statement = delete(projects_physical_objects_data).where(
        projects_physical_objects_data.c.physical_object_id == physical_object_id
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence"
    ) as mock_check_existence:
        result = await delete_physical_object_from_db(
            mock_conn, scenario_id, physical_object_id, is_scenario_object, user
        )
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await delete_physical_object_from_db(mock_conn, scenario_id, physical_object_id, is_scenario_object, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_any_call(str(delete_statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_update_physical_objects_by_function_id_to_db(
    mock_conn: MockConnection, physical_object_with_geometry_post_req: PhysicalObjectWithGeometryPost
):
    """Test the update_physical_objects_by_function_id_to_db function."""

    # Arrange
    scenario_id = 1
    physical_objects = [physical_object_with_geometry_post_req]
    user = UserDTO(id="mock_string", is_superuser=False)
    physical_object_function_id = 1
    territories_statement = select(territories_data.c.territory_id).where(
        territories_data.c.territory_id.in_({obj.territory_id for obj in physical_objects})
    )
    physical_object_types_statement = select(physical_object_types_dict.c.physical_object_function_id).where(
        physical_object_types_dict.c.physical_object_type_id.in_(
            {obj.physical_object_type_id for obj in physical_objects}
        )
    )
    project_geometry = (
        select(projects_territory_data.c.geometry)
        .where(projects_territory_data.c.project_id == 1)
        .cte(name="project_geometry")
    )
    objects_intersecting = (
        select(object_geometries_data.c.object_geometry_id)
        .where(ST_Intersects(object_geometries_data.c.geometry, project_geometry.c.geometry))
        .cte(name="objects_intersecting")
    )
    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id).where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.isnot(None),
        )
    ).cte(name="public_urban_object_ids")
    public_urban_objects_query = (
        select(urban_objects_data.c.urban_object_id)
        .select_from(
            urban_objects_data.join(
                physical_objects_data,
                physical_objects_data.c.physical_object_id == urban_objects_data.c.physical_object_id,
            )
            .join(
                physical_object_types_dict,
                physical_object_types_dict.c.physical_object_type_id == physical_objects_data.c.physical_object_type_id,
            )
            .join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids)),
            object_geometries_data.c.object_geometry_id.in_(select(objects_intersecting)),
            physical_object_types_dict.c.physical_object_function_id == physical_object_function_id,
        )
        .cte(name="public_urban_objects_query")
    )
    insert_public_urban_objects_query = insert(projects_urban_objects_data).from_select(
        (
            projects_urban_objects_data.c.scenario_id,
            projects_urban_objects_data.c.public_urban_object_id,
        ),
        select(
            literal(scenario_id).label("scenario_id"),
            public_urban_objects_query.c.urban_object_id,
        ),
    )
    insert_physical_objects_statement = (
        insert(projects_physical_objects_data)
        .values(
            [
                {
                    "public_physical_object_id": None,
                    "physical_object_type_id": physical_object.physical_object_type_id,
                    "name": physical_object.name,
                    "properties": physical_object.properties,
                }
                for physical_object in physical_objects
            ]
        )
        .returning(projects_physical_objects_data.c.physical_object_id)
    )
    insert_object_geometries_statement = (
        insert(projects_object_geometries_data)
        .values(
            [
                {
                    "public_object_geometry_id": None,
                    "territory_id": physical_object.territory_id,
                    "geometry": ST_GeomFromWKB(physical_object.geometry.as_shapely_geometry().wkb, text(str(SRID))),
                    "centre_point": ST_GeomFromWKB(
                        physical_object.centre_point.as_shapely_geometry().wkb, text(str(SRID))
                    ),
                    "address": physical_object.address,
                    "osm_id": physical_object.osm_id,
                }
                for physical_object in physical_objects
            ]
        )
        .returning(projects_object_geometries_data.c.object_geometry_id)
    )
    insert_urban_objects_statement = (
        insert(projects_urban_objects_data)
        .values(
            [
                {
                    "scenario_id": scenario_id,
                    "physical_object_id": 1,
                    "object_geometry_id": 1,
                }
            ]
        )
        .returning(urban_objects_data.c.urban_object_id)
    )

    # Act
    result = await update_physical_objects_by_function_id_to_db(
        mock_conn, physical_objects, scenario_id, user, physical_object_function_id
    )

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, ScenarioUrbanObjectDTO) for item in result
    ), "Each item should be a ScenarioUrbanObjectDTO."
    assert isinstance(
        ScenarioUrbanObject.from_dto(result[0]), ScenarioUrbanObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(territories_statement))
    mock_conn.execute_mock.assert_any_call(str(physical_object_types_statement))
    mock_conn.execute_mock.assert_any_call(str(insert_public_urban_objects_query))
    mock_conn.execute_mock.assert_any_call(str(insert_physical_objects_statement))
    mock_conn.execute_mock.assert_any_call(str(insert_object_geometries_statement))
    mock_conn.execute_mock.assert_any_call(str(insert_urban_objects_statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_add_building_to_scenario_physical_object(
    mock_conn: MockConnection, scenario_building_post_req: ScenarioBuildingPost
):
    """Test the add_building_to_db function."""

    # Arrange
    async def check_physical_object(conn, table, conditions, not_conditions=None):
        if table == projects_physical_objects_data:
            return False
        return True

    async def check_building(conn, table, conditions, not_conditions=None):
        if table == projects_buildings_data:
            return False
        return True

    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=True)
    scenario_statement_insert = (
        insert(projects_buildings_data)
        .values(**scenario_building_post_req.model_dump(exclude={"is_scenario_object"}))
        .returning(projects_buildings_data.c.building_id)
    )

    # Act
    with pytest.raises(EntityAlreadyExists):
        await add_building_to_db(mock_conn, scenario_building_post_req, scenario_id, user)
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object),
    ):
        with pytest.raises(EntityNotFoundById):
            await add_building_to_db(mock_conn, scenario_building_post_req, scenario_id, user)
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_building),
    ):
        result = await add_building_to_db(mock_conn, scenario_building_post_req, scenario_id, user)

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(scenario_statement_insert))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_put_building_to_db(mock_conn: MockConnection, scenario_building_put_req: ScenarioBuildingPut):
    """Test the put_building_to_db function."""

    # Arrange
    async def check_physical_object(conn, table, conditions, not_conditions=None):
        if table == projects_physical_objects_data:
            return False
        return True

    async def check_building(conn, table, conditions, not_conditions=None):
        if table == projects_buildings_data:
            return False
        return True

    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=True)
    statement_insert = insert(projects_buildings_data).values(
        **scenario_building_put_req.model_dump(exclude={"is_scenario_object"})
    )
    statement_update = (
        update(projects_buildings_data)
        .where(projects_buildings_data.c.physical_object_id == scenario_building_put_req.physical_object_id)
        .values(**scenario_building_put_req.model_dump(exclude={"is_scenario_object"}))
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_physical_object),
    ):
        with pytest.raises(EntityNotFoundById):
            await put_building_to_db(mock_conn, scenario_building_put_req, scenario_id, user)
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_building),
    ):
        await put_building_to_db(mock_conn, scenario_building_put_req, scenario_id, user)
    result = await put_building_to_db(mock_conn, scenario_building_put_req, scenario_id, user)

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement_insert))
    mock_conn.execute_mock.assert_any_call(str(statement_update))
    assert mock_conn.commit_mock.call_count == 2, "Commit mock count should be one for one method."


@pytest.mark.asyncio
async def test_patch_building_to_db(mock_conn: MockConnection, scenario_building_patch_req: ScenarioBuildingPatch):
    """Test the patch_building_to_db function."""

    # Arrange
    building_id = 1
    is_scenario_object = True
    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=True)

    async def check_building_id(conn, table, conditions, not_conditions=None):
        if table == projects_buildings_data:
            return False
        return True

    statement_update = (
        update(projects_buildings_data)
        .where(projects_buildings_data.c.building_id == building_id)
        .values(**scenario_building_patch_req.model_dump(exclude_unset=True))
        .returning(projects_buildings_data.c.physical_object_id)
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence",
        new=AsyncMock(side_effect=check_building_id),
    ):
        with pytest.raises(EntityNotFoundById):
            await patch_building_to_db(
                mock_conn, scenario_building_patch_req, building_id, is_scenario_object, scenario_id, user
            )
    result = await patch_building_to_db(
        mock_conn, scenario_building_patch_req, scenario_id, building_id, is_scenario_object, user
    )

    # Assert
    assert isinstance(result, ScenarioPhysicalObjectDTO), "Result should be a ScenarioPhysicalObjectDTO."
    assert isinstance(
        ScenarioPhysicalObject.from_dto(result), ScenarioPhysicalObject
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement_update))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_scenario_building_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_in_db function."""

    # Arrange
    building_id = 1
    is_scenario_object = True
    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=True)
    statement_delete = delete(projects_buildings_data).where(projects_buildings_data.c.building_id == building_id)

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_physical_objects.check_existence"
    ) as mock_check_existence:
        result = await delete_building_from_db(mock_conn, scenario_id, building_id, is_scenario_object, user)
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await delete_building_from_db(mock_conn, scenario_id, building_id, is_scenario_object, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_any_call(str(statement_delete))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_public_building_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_in_db function."""

    # Arrange
    building_id = 1
    is_scenario_object = False
    scenario_id = 1
    user = UserDTO(id="mock_string", is_superuser=True)
    insert_scenario_physical_object_statement = (
        insert(projects_physical_objects_data)
        .from_select(
            [
                "physical_object_type_id",
                "name",
                "properties",
                "public_physical_object_id",
            ],
            select(
                physical_objects_data.c.physical_object_type_id,
                physical_objects_data.c.name,
                physical_objects_data.c.properties,
                literal(1).label("public_physical_object_id"),
            ).where(physical_objects_data.c.physical_object_id == 1),
        )
        .returning(projects_physical_objects_data.c.physical_object_id)
    )
    project_geometry = (
        select(projects_territory_data.c.geometry).where(projects_territory_data.c.project_id == 1)
    ).alias("project_geometry")
    public_urban_object_ids = (
        select(projects_urban_objects_data.c.public_urban_object_id.label("urban_object_id"))
        .where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.is_not(None),
        )
        .alias("public_urban_object_ids")
    )
    select_urban_objects_statement = (
        select(urban_objects_data)
        .select_from(
            urban_objects_data.join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.physical_object_id == 1,
            urban_objects_data.c.urban_object_id.not_in(select(public_urban_object_ids.c.urban_object_id)),
            ST_Within(object_geometries_data.c.geometry, select(project_geometry).scalar_subquery()),
        )
    )
    update_urban_objects_statement = (
        update(projects_urban_objects_data)
        .where(projects_urban_objects_data.c.public_physical_object_id == 1)
        .values(physical_object_id=1, public_physical_object_id=None)
    )

    # Act
    result = await delete_building_from_db(mock_conn, scenario_id, building_id, is_scenario_object, user)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_any_call(str(insert_scenario_physical_object_statement))
    mock_conn.execute_mock.assert_any_call(str(select_urban_objects_statement))
    mock_conn.execute_mock.assert_any_call(str(update_urban_objects_statement))
    mock_conn.commit_mock.assert_called_once()
