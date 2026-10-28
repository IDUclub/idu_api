"""Spatial selection of compact services in a scenario."""

from typing import Literal

from geoalchemy2.functions import ST_AsEWKB, ST_Intersection, ST_Intersects, ST_Within
from geoalchemy2.shape import from_shape
from shapely.geometry.base import BaseGeometry
from sqlalchemy import case, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.functions import coalesce

from idu_api.common.db.entities import (
    object_geometries_data,
    projects_object_geometries_data,
    projects_services_data,
    projects_territory_data,
    projects_urban_objects_data,
    service_types_dict,
    services_data,
    urban_objects_data,
)
from idu_api.urban_api.dto.services import ScenarioServiceGeometryDTO
from idu_api.urban_api.dto.users import UserDTO
from idu_api.urban_api.logic.impl.helpers.projects_scenarios import check_scenario
from idu_api.urban_api.logic.impl.helpers.utils import include_child_territories_cte


async def get_services_by_geometry_from_db(  # pylint: disable=too-many-locals
    conn: AsyncConnection,
    scenario_id: int,
    geometry: BaseGeometry,
    user: UserDTO | None,
    service_type_id: int | None = None,
    intersection_type: Literal["intersects", "within"] = "intersects",
) -> list[ScenarioServiceGeometryDTO]:
    """Filter visible scenario geometries; local project geometries are clipped to its boundary.

    ``within`` uses ST_Within: a point or line lying only on the search boundary
    does not qualify. Intersections include boundary contact.
    """
    if intersection_type not in ("intersects", "within"):
        raise ValueError("intersection_type must be 'intersects' or 'within'")
    scenario = await check_scenario(conn, scenario_id, user, return_value=True)
    search_geometry = from_shape(geometry, srid=4326)
    project_geometry = None
    if not scenario.is_regional:
        project_geometry = (
            select(projects_territory_data.c.geometry)
            .where(projects_territory_data.c.project_id == scenario.project_id)
            .scalar_subquery()
        )

    excluded_objects = select(projects_urban_objects_data.c.public_urban_object_id).where(
        projects_urban_objects_data.c.scenario_id == scenario_id,
        projects_urban_objects_data.c.public_urban_object_id.isnot(None),
    )
    public_geometry = object_geometries_data.c.geometry
    visible_public_geometry = (
        ST_Intersection(public_geometry, project_geometry) if project_geometry is not None else public_geometry
    )
    public_query = (
        select(
            services_data.c.service_id,
            services_data.c.service_type_id,
            services_data.c.name,
            services_data.c.capacity,
            services_data.c.is_capacity_real,
            object_geometries_data.c.object_geometry_id,
            visible_public_geometry.label("geometry"),
            literal(False).label("is_scenario_service"),
            literal(False).label("is_scenario_geometry"),
            (~ST_Within(public_geometry, project_geometry) if project_geometry is not None else literal(False)).label(
                "is_locked"
            ),
        )
        .select_from(
            urban_objects_data.join(services_data, services_data.c.service_id == urban_objects_data.c.service_id).join(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == urban_objects_data.c.object_geometry_id,
            )
        )
        .where(
            urban_objects_data.c.urban_object_id.not_in(excluded_objects),
            ST_Intersects(public_geometry, search_geometry),
        )
    )
    if project_geometry is not None:
        public_query = public_query.where(ST_Intersects(public_geometry, project_geometry))
    else:
        territories = include_child_territories_cte(scenario.territory_id)
        public_query = public_query.where(object_geometries_data.c.territory_id.in_(select(territories.c.territory_id)))

    # A scenario service replaces the entire public service, including nullable attributes.
    effective_columns = [
        case(
            (projects_services_data.c.service_id.isnot(None), projects_services_data.c[key]), else_=services_data.c[key]
        ).label(key)
        for key in ("service_id", "service_type_id", "name", "capacity", "is_capacity_real")
    ]
    effective_geometry = coalesce(projects_object_geometries_data.c.geometry, public_geometry)
    visible_scenario_geometry = (
        ST_Intersection(effective_geometry, project_geometry) if project_geometry is not None else effective_geometry
    )
    scenario_query = (
        select(
            *effective_columns,
            coalesce(
                projects_object_geometries_data.c.object_geometry_id, object_geometries_data.c.object_geometry_id
            ).label("object_geometry_id"),
            visible_scenario_geometry.label("geometry"),
            projects_urban_objects_data.c.service_id.isnot(None).label("is_scenario_service"),
            projects_urban_objects_data.c.object_geometry_id.isnot(None).label("is_scenario_geometry"),
            literal(False).label("is_locked"),
        )
        .select_from(
            projects_urban_objects_data.outerjoin(
                projects_services_data, projects_services_data.c.service_id == projects_urban_objects_data.c.service_id
            )
            .outerjoin(services_data, services_data.c.service_id == projects_urban_objects_data.c.public_service_id)
            .outerjoin(
                projects_object_geometries_data,
                projects_object_geometries_data.c.object_geometry_id
                == projects_urban_objects_data.c.object_geometry_id,
            )
            .outerjoin(
                object_geometries_data,
                object_geometries_data.c.object_geometry_id == projects_urban_objects_data.c.public_object_geometry_id,
            )
        )
        .where(
            projects_urban_objects_data.c.scenario_id == scenario_id,
            projects_urban_objects_data.c.public_urban_object_id.is_(None),
            ST_Intersects(effective_geometry, search_geometry),
        )
    )
    if service_type_id is not None:
        public_query = public_query.where(services_data.c.service_type_id == service_type_id)
        scenario_query = scenario_query.where(effective_columns[1] == service_type_id)

    rows = union_all(public_query, scenario_query).cte("scenario_services_geometry")
    predicate = ST_Within if intersection_type == "within" else ST_Intersects
    statement = (
        select(
            *(column for column in rows.c if column.key != "geometry"),
            service_types_dict.c.name.label("service_type_name"),
            ST_AsEWKB(rows.c.geometry).label("geometry"),
        )
        .select_from(rows.join(service_types_dict, service_types_dict.c.service_type_id == rows.c.service_type_id))
        .where(predicate(rows.c.geometry, search_geometry))
        .distinct()
        .order_by(rows.c.is_scenario_service, rows.c.service_id, rows.c.object_geometry_id)
    )
    result = (await conn.execute(statement)).mappings().all()
    return [ScenarioServiceGeometryDTO(**row) for row in result]
