"""Regression coverage for asyncpg's bind-parameter limit during scenario copying."""

from collections import Counter
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects.postgresql.asyncpg import dialect

from idu_api.urban_api.logic.impl.helpers import projects_objects as helpers
from tests.urban_api.helpers.connection import MockResult, MockRow


def urban_row(**overrides):
    values = dict(
        public_urban_object_id=None,
        object_geometry_id=1,
        physical_object_id=2,
        service_id=3,
        public_object_geometry_id=None,
        public_physical_object_id=None,
        public_service_id=None,
    )
    return MockRow(**(values | overrides))


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 1, 40000])
async def test_regional_copy_bounds_parameters_and_preserves_rows(monkeypatch, count):
    rows = [urban_row(object_geometry_id=i) for i in range(1, count + 1)]
    if rows:
        rows.extend(
            [
                urban_row(public_urban_object_id=99),
                urban_row(public_object_geometry_id=5, public_physical_object_id=6, public_service_id=7),
                urban_row(object_geometry_id=None, physical_object_id=None, service_id=None),
                urban_row(public_object_geometry_id=999),
            ]
        )
    geometries = {i: i + 100000 for i in range(1, count + 1)}
    monkeypatch.setattr(helpers, "copy_geometries", AsyncMock(side_effect=[geometries, {5: 200005}]))
    monkeypatch.setattr(helpers, "copy_physical_objects", AsyncMock(return_value={2: 200002}))
    monkeypatch.setattr(helpers, "copy_services", AsyncMock(return_value={3: 200003}))
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=MockResult(rows))

    await helpers.copy_urban_objects_from_regional_scenario(conn, 10, "geometry", 20)

    inserted = []
    for call in conn.execute.call_args_list[1:]:
        compiled = call.args[0].compile(dialect=dialect(), compile_kwargs={"render_postcompile": True})
        assert len(compiled.positiontup) < 32767
        assert "CASE" not in str(compiled)
        batch = {}
        for key, value in compiled.params.items():
            column, index = key.rsplit("_m", 1)
            batch.setdefault(int(index), {})[column] = value
        assert len(batch) <= 1000
        inserted.extend(batch.values())

    expected = []
    for row in rows:
        if row.public_urban_object_id is not None:
            expected.append({"scenario_id": 20, "public_urban_object_id": 99})
        else:
            expected.append(
                dict(
                    scenario_id=20,
                    object_geometry_id=(
                        {5: 200005}.get(row.public_object_geometry_id)
                        if row.public_object_geometry_id is not None
                        else geometries.get(row.object_geometry_id)
                    ),
                    physical_object_id=200002 if row.physical_object_id == 2 else None,
                    service_id=200003 if row.service_id == 3 else None,
                    public_object_geometry_id=None,
                    public_physical_object_id=row.public_physical_object_id,
                    public_service_id=row.public_service_id,
                )
            )
    # Public and project records are inserted separately within each batch.
    assert Counter(tuple(sorted(row.items())) for row in inserted) == Counter(
        tuple(sorted(row.items())) for row in expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "helper,kwargs",
    [
        (helpers.copy_geometries, {}),
        (helpers.copy_geometries, {"is_from_public": True, "geometry": "geometry"}),
        (helpers.copy_physical_objects, {}),
        (helpers.copy_services, {}),
    ],
)
@pytest.mark.parametrize("count", [0, 40000])
async def test_copy_helpers_bind_ids_as_one_array(helper, kwargs, count):
    ids = list(range(1, count + 1))
    new_ids = [value + 100000 for value in ids]
    result = MagicMock()
    result.scalars.return_value.all.return_value = new_ids
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=result)

    assert await helper(conn, ids, **kwargs) == dict(zip(ids, new_ids))
    if not ids:
        conn.execute.assert_not_called()
        return
    compiled = conn.execute.call_args.args[0].compile(dialect=dialect(), compile_kwargs={"render_postcompile": True})
    assert len(compiled.positiontup) < 10
    assert "ANY (" in str(compiled)
    assert ids in compiled.params.values()
