"""Regression tests for scenario isolation and asyncpg's bind parameter limit."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg

from idu_api.urban_api.logic.impl.helpers import projects_objects, projects_physical_objects, projects_scenarios
from tests.urban_api.helpers.connection import MockConnection, MockResult, MockRow


class LocalConnection:
    """Execute relational queries locally, checking PostgreSQL bind counts too."""

    def __init__(self, connection):
        self.connection = connection
        self.statements = []

    async def execute(self, statement):
        compiled = statement.compile(dialect=PGDialect_asyncpg(), compile_kwargs={"render_postcompile": True})
        assert len(compiled.positiontup) <= 32767, "asyncpg bind parameter limit exceeded"
        self.statements.append(statement)
        return self.connection.execute(statement)

    async def commit(self):
        self.connection.commit()


@pytest.fixture
def local_conn():
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(text("ATTACH DATABASE ':memory:' AS public"))
        connection.execute(text("ATTACH DATABASE ':memory:' AS user_projects"))
        connection.execute(
            text(
                "CREATE TABLE public.urban_objects_data "
                "(urban_object_id INTEGER PRIMARY KEY, physical_object_id INTEGER, "
                "object_geometry_id INTEGER, service_id INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE user_projects.object_geometries_data "
                "(object_geometry_id INTEGER PRIMARY KEY, public_object_geometry_id INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE user_projects.urban_objects_data "
                "(urban_object_id INTEGER PRIMARY KEY, scenario_id INTEGER, "
                "public_urban_object_id INTEGER, object_geometry_id INTEGER, "
                "physical_object_id INTEGER, service_id INTEGER, public_object_geometry_id INTEGER, "
                "public_physical_object_id INTEGER, public_service_id INTEGER)"
            )
        )
        yield LocalConnection(connection)
    engine.dispose()


@pytest.mark.asyncio
async def test_new_projects_only_use_their_mapped_geometries(local_conn):
    """Creating projects repeatedly must not pick up geometries of earlier projects."""
    connection = local_conn.connection
    connection.execute(
        text("INSERT INTO public.urban_objects_data VALUES (1, 4351197, 10, NULL), (2, 4351197, 10, 20)")
    )

    for scenario_id in range(1, 6):
        geometry_id = 100 + scenario_id
        connection.execute(
            text("INSERT INTO user_projects.object_geometries_data VALUES (:id, 10)"), {"id": geometry_id}
        )
        mapping = await projects_objects.insert_urban_objects(local_conn, scenario_id, {10: geometry_id})
        assert len(mapping) == 2
        rows = connection.execute(
            text(
                "SELECT public_urban_object_id, object_geometry_id, public_service_id "
                "FROM user_projects.urban_objects_data WHERE scenario_id = :id "
                "ORDER BY urban_object_id"
            ),
            {"id": scenario_id},
        ).all()
        assert rows == [(1, None, None), (2, None, None), (None, geometry_id, None), (None, geometry_id, 20)]


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, 2001])
async def test_insert_mapped_geometries_uses_bounded_queries(local_conn, size):
    connection = local_conn.connection
    if size:
        connection.execute(
            text("INSERT INTO public.urban_objects_data VALUES (:id, 4351197, :id, NULL)"),
            [{"id": i} for i in range(1, size + 1)],
        )
        connection.execute(
            text("INSERT INTO user_projects.object_geometries_data VALUES (:id + 50000, :id)"),
            [{"id": i} for i in range(1, size + 1)],
        )
    mapping = await projects_objects.insert_urban_objects(local_conn, 1, {i: i + 50000 for i in range(1, size + 1)})
    assert len(mapping) == size
    assert connection.scalar(text("SELECT COUNT(*) FROM user_projects.urban_objects_data")) == size * 2
    rows = (
        connection.execute(
            text(
                "SELECT object_geometry_id FROM user_projects.urban_objects_data "
                "WHERE object_geometry_id IS NOT NULL ORDER BY object_geometry_id"
            )
        )
        .scalars()
        .all()
    )
    assert rows == list(range(50001, 50001 + size))


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, 1, 20480])
async def test_copy_scenario_preserves_links_with_bounded_queries(local_conn, size):
    """Large scenarios retain every mapped link without generating an oversized CASE."""
    connection = local_conn.connection
    if size:
        connection.execute(
            text(
                "INSERT INTO user_projects.urban_objects_data "
                "(scenario_id, object_geometry_id, physical_object_id, service_id) "
                "VALUES (1, :id, 7, 8)"
            ),
            [{"id": i} for i in range(1, size + 1)],
        )
    connection.execute(
        text("INSERT INTO user_projects.urban_objects_data " "(scenario_id, public_urban_object_id) VALUES (1, 100)")
    )
    connection.execute(
        text(
            "INSERT INTO user_projects.urban_objects_data "
            "(scenario_id, public_object_geometry_id, public_physical_object_id, public_service_id) "
            "VALUES (1, 10, 4351197, 20)"
        )
    )
    with (
        patch.object(
            projects_scenarios, "copy_geometries", AsyncMock(return_value={i: i + 50000 for i in range(1, size + 1)})
        ),
        patch.object(projects_scenarios, "copy_physical_objects", AsyncMock(return_value={7: 70})),
        patch.object(projects_scenarios, "copy_services", AsyncMock(return_value={8: 80})),
    ):
        await projects_scenarios._copy_urban_objects(local_conn, 1, 2)
    rows = connection.execute(
        text(
            "SELECT object_geometry_id, physical_object_id, service_id "
            "FROM user_projects.urban_objects_data WHERE scenario_id = 2 "
            "AND object_geometry_id IS NOT NULL ORDER BY object_geometry_id"
        )
    ).all()
    assert rows == [(i + 50000, 70, 80) for i in range(1, size + 1)]
    assert (
        connection.scalar(text("SELECT COUNT(*) FROM user_projects.urban_objects_data WHERE scenario_id = 2"))
        == size + 2
    )
    assert (
        connection.scalar(text("SELECT COUNT(*) FROM user_projects.urban_objects_data WHERE scenario_id = 1"))
        == size + 2
    )
    assert connection.execute(
        text(
            "SELECT public_urban_object_id, public_object_geometry_id, public_physical_object_id, "
            "public_service_id FROM user_projects.urban_objects_data "
            "WHERE scenario_id = 2 AND object_geometry_id IS NULL ORDER BY urban_object_id"
        )
    ).all() == [(100, None, None, None), (None, 10, 4351197, 20)]


@pytest.mark.asyncio
async def test_deleting_public_object_is_scoped_to_current_scenario():
    conn = AsyncMock()
    conn.execute.return_value = MockResult([])
    scenario = SimpleNamespace(is_regional=False, project_id=1546)
    with (
        patch.object(projects_physical_objects, "check_scenario", AsyncMock(return_value=scenario)),
        patch.object(projects_physical_objects, "check_existence", AsyncMock(return_value=True)),
    ):
        await projects_physical_objects.delete_physical_object_from_db(conn, 10298, 4351197, False, None)
    deletes = [call.args[0] for call in conn.execute.call_args_list if call.args[0].is_delete]
    assert len(deletes) == 1
    compiled = deletes[0].compile()
    assert "urban_objects_data.scenario_id =" in str(compiled)
    assert 10298 in compiled.params.values()


@pytest.mark.asyncio
async def test_base_scenario_creation_keeps_regional_source_unchanged():
    """Cropped public objects belong to the new base, never to its regional source."""
    conn = MockConnection(preset_results=[MockResult([MockRow(is_regional=False, territory_id=1, geometry="geom")])])
    with (
        patch.object(projects_objects, "check_existence", AsyncMock(return_value=False)),
        patch.object(projects_objects, "create_project_base_scenario", AsyncMock(return_value=(10298, 10286))),
        patch.object(projects_objects, "copy_urban_objects_from_regional_scenario", AsyncMock()),
        patch.object(projects_objects, "insert_intersecting_geometries", AsyncMock(return_value={10: 100})),
        patch.object(projects_objects, "insert_urban_objects", AsyncMock(return_value={})) as insert_objects,
        patch.object(projects_objects, "copy_buffers", AsyncMock()),
        patch.object(projects_objects, "insert_functional_zones", AsyncMock()),
    ):
        await projects_objects.create_base_scenario_to_db(conn, 1546, 10286, AsyncMock())
    insert_objects.assert_awaited_once_with(conn, 10298, {10: 100})
