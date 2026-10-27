"""Spatial scenario service queries and their HTTP representations."""

import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import shapely
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from shapely.geometry import Point, box, mapping
from sqlalchemy.dialects import sqlite

from idu_api.urban_api.dependencies import auth_dep
from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.exceptions.logic.common import EntityNotFoundById
from idu_api.urban_api.exceptions.logic.users import AccessDeniedError
from idu_api.urban_api.handlers.v1.projects import services as handlers
from idu_api.urban_api.logic.impl import projects
from tests.urban_api.helpers.connection import MockConnection, MockResult, MockRow

AREA = box(0, 0, 10, 10)
OWNER = UserDTO(id="owner", username="owner", roles=[], is_superuser=False, azp="test")


class SpatialConnection:
    """Execute the production SQL with SQLite and GEOS instead of a PostGIS server."""

    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("ATTACH DATABASE ':memory:' AS user_projects")
        self.db.executescript(
            """
            CREATE TABLE services_data
                (service_id INTEGER, service_type_id INTEGER, name TEXT, capacity INTEGER, is_capacity_real BOOLEAN);
            CREATE TABLE service_types_dict (service_type_id INTEGER, name TEXT);
            CREATE TABLE object_geometries_data (object_geometry_id INTEGER, territory_id INTEGER, geometry BLOB);
            CREATE TABLE urban_objects_data (urban_object_id INTEGER, object_geometry_id INTEGER, service_id INTEGER);
            CREATE TABLE territories_data (territory_id INTEGER, parent_id INTEGER, is_city BOOLEAN);
            CREATE TABLE user_projects.services_data
                (service_id INTEGER, service_type_id INTEGER, name TEXT, capacity INTEGER, is_capacity_real BOOLEAN);
            CREATE TABLE user_projects.object_geometries_data (object_geometry_id INTEGER, geometry BLOB);
            CREATE TABLE user_projects.urban_objects_data
                (urban_object_id INTEGER, scenario_id INTEGER, public_urban_object_id INTEGER,
                 object_geometry_id INTEGER, public_object_geometry_id INTEGER, service_id INTEGER,
                 public_service_id INTEGER);
            CREATE TABLE user_projects.projects_territory_data (project_id INTEGER, geometry BLOB);
            INSERT INTO service_types_dict VALUES (1, 'School'), (2, 'Hospital');
            INSERT INTO territories_data VALUES (1, NULL, 0), (2, 1, 0), (3, NULL, 0);
            """
        )
        self.db.create_function("ST_GeomFromWKB", 2, lambda value, srid: value)
        self.db.create_function("ST_AsEWKB", 1, lambda value: value)
        self.db.create_function("AsEWKB", 1, lambda value: value)
        for name, predicate in [("ST_Intersects", shapely.intersects), ("ST_Within", shapely.within)]:
            self.db.create_function(
                name, 2, lambda left, right, fn=predicate: bool(fn(shapely.from_wkb(left), shapely.from_wkb(right)))
            )
        self.db.create_function(
            "ST_Intersection",
            2,
            lambda left, right: shapely.intersection(shapely.from_wkb(left), shapely.from_wkb(right)).wkb,
        )
        self.statements = []

    def add_public(self, identifier, geometry, service_type_id=1, territory_id=2):
        self.db.execute(
            "INSERT INTO services_data VALUES (?, ?, ?, 50, 1)", (identifier, service_type_id, f"Service {identifier}")
        )
        self.db.execute("INSERT INTO object_geometries_data VALUES (?, ?, ?)", (identifier, territory_id, geometry.wkb))
        self.db.execute("INSERT INTO urban_objects_data VALUES (?, ?, ?)", (identifier, identifier, identifier))

    async def execute(self, statement):
        self.statements.append(statement)
        compiled = statement.compile(dialect=sqlite.dialect(), compile_kwargs={"render_postcompile": True})
        parameters = compiled.params
        for key, bind in compiled.binds.items():
            processor = bind.type.bind_processor(sqlite.dialect())
            if key in parameters and processor is not None:
                parameters[key] = processor(parameters[key])
        rows = self.db.execute(str(compiled), [parameters[key] for key in compiled.positiontup]).fetchall()
        return MockResult([MockRow(**dict(row)) for row in rows])


@pytest.fixture(name="spatial_conn")
def spatial_connection_fixture():
    conn = SpatialConnection()
    yield conn
    conn.db.close()


async def fetch(conn, **kwargs):
    helper = getattr(projects, "get_services_by_geometry_from_db", None)
    assert helper is not None, "The spatial scenario service method is missing"
    scenario = SimpleNamespace(is_regional=kwargs.pop("regional", True), territory_id=1, project_id=1)
    geometry = kwargs.pop("geometry", AREA)
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_services_geometry.check_scenario",
        new_callable=AsyncMock,
        return_value=scenario,
    ) as check:
        result = await helper(conn, 7, geometry, OWNER, **kwargs)
        check.assert_awaited_once_with(conn, 7, OWNER, return_value=True)
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("intersection_type,expected", [("intersects", {1, 2, 3}), ("within", {1})])
async def test_spatial_predicates_and_geometry_are_preserved(spatial_conn, intersection_type, expected):
    geometries = {1: box(1, 1, 2, 2), 2: box(9, 9, 12, 12), 3: Point(0, 5), 4: box(20, 20, 21, 21)}
    for identifier, geometry in geometries.items():
        spatial_conn.add_public(identifier, geometry)
    result = await fetch(spatial_conn, intersection_type=intersection_type)
    assert {row.service_id for row in result} == expected
    assert all(row.geometry.equals(geometries[row.service_id]) for row in result)


@pytest.mark.asyncio
@pytest.mark.parametrize("service_type_id,expected", [(None, {1, 2}), (1, {1}), (2, {2}), (999, set())])
async def test_optional_type_and_regional_scope(spatial_conn, service_type_id, expected):
    spatial_conn.add_public(1, Point(1, 1))
    spatial_conn.add_public(2, Point(2, 2), service_type_id=2, territory_id=1)
    spatial_conn.add_public(3, Point(3, 3), territory_id=3)
    result = await fetch(spatial_conn, service_type_id=service_type_id)
    assert {row.service_id for row in result} == expected
    sql = str(spatial_conn.statements[-1])
    for field in [
        "created_at",
        "updated_at",
        "properties",
        "urban_functions_dict",
        "territory_types_dict",
        "centre_point",
    ]:
        assert field not in sql


@pytest.mark.asyncio
async def test_scenario_replacements_deletions_and_other_scenarios(spatial_conn):
    for identifier in range(1, 5):
        spatial_conn.add_public(identifier, Point(identifier, identifier))
    spatial_conn.db.executescript(
        """
        INSERT INTO user_projects.services_data VALUES (1, 2, NULL, NULL, NULL), (5, 1, 'New', 10, 1);
        INSERT INTO user_projects.urban_objects_data VALUES
            (1, 7, 1, NULL, NULL, NULL, NULL),
            (2, 7, NULL, NULL, 1, 1, 1),
            (3, 7, 2, NULL, NULL, NULL, NULL),
            (4, 8, 3, NULL, NULL, NULL, NULL),
            (5, 7, NULL, 5, NULL, 5, NULL),
            (6, 8, NULL, 5, NULL, 5, NULL),
            (7, 7, 4, NULL, NULL, NULL, NULL),
            (8, 7, NULL, 5, NULL, NULL, 4);
        """
    )
    spatial_conn.db.execute("INSERT INTO user_projects.object_geometries_data VALUES (5, ?)", (Point(5, 5).wkb,))
    result = await fetch(spatial_conn)
    assert {(row.service_id, bool(row.is_scenario_service)) for row in result} == {
        (1, True),
        (3, False),
        (4, False),
        (5, True),
    }
    edited = next(row for row in result if row.service_id == 1)
    assert edited.service_type_id == 2
    assert edited.name is None and edited.capacity is None and edited.is_capacity_real is None
    moved = next(row for row in result if row.service_id == 4)
    assert moved.geometry.equals(Point(5, 5)) and moved.is_scenario_geometry
    filtered = await fetch(spatial_conn, service_type_id=2)
    assert [row.service_id for row in filtered] == [1]


@pytest.mark.asyncio
async def test_local_project_scope_and_clipping(spatial_conn):
    spatial_conn.add_public(1, box(1, 1, 4, 4))
    spatial_conn.add_public(2, Point(8, 8))
    spatial_conn.db.execute("INSERT INTO user_projects.projects_territory_data VALUES (1, ?)", (box(0, 0, 3, 3).wkb,))
    result = await fetch(spatial_conn, regional=False)
    assert [row.service_id for row in result] == [1]
    assert result[0].geometry.equals(box(1, 1, 3, 3))
    assert result[0].is_locked


@pytest.mark.asyncio
async def test_duplicate_physical_bindings_keep_one_row_per_service_geometry(spatial_conn):
    spatial_conn.add_public(1, Point(1, 1))
    spatial_conn.db.execute("INSERT INTO urban_objects_data VALUES (2, 1, 1)")
    spatial_conn.db.execute("INSERT INTO object_geometries_data VALUES (2, 2, ?)", (Point(2, 2).wkb,))
    spatial_conn.db.execute("INSERT INTO urban_objects_data VALUES (3, 2, 1)")
    result = await fetch(spatial_conn)
    assert [(row.service_id, row.object_geometry_id) for row in result] == [(1, 1), (1, 2)]


@pytest.mark.asyncio
async def test_within_accepts_equal_geometry(spatial_conn):
    spatial_conn.add_public(1, AREA)
    spatial_conn.add_public(2, box(0, 0, 10, 10).difference(box(4, 4, 6, 6)))
    assert {row.service_id for row in await fetch(spatial_conn, intersection_type="within")} == {1, 2}


@pytest.mark.asyncio
@pytest.mark.parametrize("intersection_type", ["intersects", "within"])
async def test_search_geometry_holes_are_excluded(spatial_conn, intersection_type):
    spatial_conn.add_public(1, Point(1, 1))
    spatial_conn.add_public(2, Point(5, 5))
    search_area = AREA.difference(box(4, 4, 6, 6))
    result = await fetch(spatial_conn, geometry=search_area, intersection_type=intersection_type)
    assert [row.service_id for row in result] == [1]


@pytest.mark.asyncio
async def test_unknown_intersection_type_is_rejected_without_querying():
    conn = MagicMock(execute=AsyncMock())
    with pytest.raises(ValueError, match="intersection_type"):
        await projects.get_services_by_geometry_from_db(conn, 7, AREA, OWNER, intersection_type="invalid")
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "public,user,exists,error",
    [
        (False, None, True, AccessDeniedError),
        (False, OWNER, False, EntityNotFoundById),
        (True, None, True, None),
        (False, OWNER, True, None),
    ],
)
async def test_access_is_checked_before_service_query(public, user, exists, error):
    helper = getattr(projects, "get_services_by_geometry_from_db", None)
    assert helper is not None, "The spatial scenario service method is missing"
    scenario = MockRow(project_id=1, user_id="owner", public=public, is_regional=True, territory_id=1)
    conn = MockConnection(preset_results=[MockResult([scenario] if exists else []), MockResult([])])
    if error is not None:
        with pytest.raises(error):
            await helper(conn, 7, AREA, user)
        assert conn.execute_mock.await_count == 1
    else:
        assert await helper(conn, 7, AREA, user) == []
        assert conn.execute_mock.await_count == 2


@pytest.fixture(name="http_app")
def http_application_fixture(spatial_conn):
    assert hasattr(handlers, "get_services_by_geometry"), "The list handler is missing"
    assert hasattr(handlers, "get_services_by_geometry_geojson"), "The GeoJSON handler is missing"
    app = FastAPI()
    app.include_router(handlers.projects_router)
    app.dependency_overrides[auth_dep.from_request_optional] = lambda: OWNER
    manager = MagicMock()
    manager.get_ro_connection.return_value.__aenter__.return_value = spatial_conn
    service = projects.UserProjectServiceImpl(manager, MagicMock())

    @app.middleware("http")
    async def inject_service(request, call_next):
        request.state.user_project_service = service
        return await call_next(request)

    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["", "/geojson"])
@pytest.mark.parametrize(
    "params,expected",
    [
        ({}, {1, 2}),
        ({"intersection_type": "within"}, {1}),
        ({"service_type_id": 2}, {2}),
        ({"service_type_id": 999}, set()),
    ],
)
async def test_http_representations(http_app, spatial_conn, suffix, params, expected):
    spatial_conn.add_public(1, Point(2, 2))
    spatial_conn.add_public(2, box(9, 9, 12, 12), service_type_id=2)
    with patch(
        "idu_api.urban_api.logic.impl.helpers.projects_services_geometry.check_scenario",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(is_regional=True, territory_id=1),
    ) as check:
        async with AsyncClient(transport=ASGITransport(app=http_app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/scenarios/7/services/by_geometry{suffix}", json=mapping(AREA), params=params
            )
    assert response.status_code == 200, response.text
    check.assert_awaited_once_with(spatial_conn, 7, OWNER, return_value=True)
    payload = response.json()
    if suffix:
        assert response.headers["content-type"] == "application/geo+json"
        assert payload["type"] == "FeatureCollection"
        rows = [{**item["properties"], "geometry": item["geometry"]} for item in payload["features"]]
    else:
        rows = payload
    assert {item["service_id"] for item in rows} == expected
    for row in rows:
        assert set(row) == {
            "service_id",
            "service_type_id",
            "service_type_name",
            "name",
            "capacity",
            "is_capacity_real",
            "object_geometry_id",
            "geometry",
            "is_scenario_service",
            "is_scenario_geometry",
            "is_locked",
        }
        assert row["geometry"]["type"] in {"Point", "Polygon"}
        expected_geometry = Point(2, 2) if row["service_id"] == 1 else box(9, 9, 12, 12)
        assert shapely.geometry.shape(row["geometry"]).equals(expected_geometry)


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["", "/geojson"])
@pytest.mark.parametrize(
    "params,body",
    [
        ({"intersection_type": "invalid"}, mapping(AREA)),
        ({"service_type_id": 0}, mapping(AREA)),
        ({}, {"type": "Polygon", "coordinates": []}),
        ({}, {"type": "Point", "coordinates": [1]}),
        ({}, {"type": "Polygon", "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]]}),
    ],
)
async def test_invalid_input_returns_422(http_app, spatial_conn, suffix, params, body):
    async with AsyncClient(transport=ASGITransport(app=http_app), base_url="http://test") as client:
        response = await client.post(f"/v1/scenarios/7/services/by_geometry{suffix}", json=body, params=params)
    assert response.status_code == 422, response.text
    assert spatial_conn.statements == []
