"""Exercise normative tools through MCP and the real territories service."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client, FastMCP
from shapely.geometry import Point, Polygon
from starlette.requests import Request

from idu_api.urban_api.dto import NormativeDTO, TerritoryWithNormativesDTO
from idu_api.urban_api.logic.impl import territories as territories_logic
from idu_api.urban_mcp.groups import MCP_GROUPS

TOOL_NAMES = {"GetTerritoryNormatives", "GetNormativesValuesGeoJSON"}


@pytest.fixture(name="normative")
def normative_fixture():
    return NormativeDTO(
        service_type_id=1,
        service_type_name="School",
        urban_function_id=None,
        urban_function_name=None,
        year=2024,
        territory_id=2,
        territory_name="City",
        is_regulated=True,
        radius_availability_meters=500,
        time_availability_minutes=None,
        services_per_1000_normative=2,
        services_capacity_per_1000_normative=None,
        normative_type="parent",
        source="Regional standard",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture(name="mcp_backend")
def mcp_backend_fixture(monkeypatch):
    connection = object()
    manager = MagicMock()
    manager.get_ro_connection.return_value = AsyncMock()
    manager.get_ro_connection.return_value.__aenter__.return_value = connection
    request = Request({"type": "http"})
    request.state.territories_service = territories_logic.TerritoriesServiceImpl(manager)
    monkeypatch.setattr("fastmcp.server.dependencies.get_http_request", lambda: request)

    by_territory = AsyncMock(return_value=[])
    by_parent = AsyncMock(return_value=[])
    monkeypatch.setattr(territories_logic, "get_normatives_by_territory_id_from_db", by_territory)
    monkeypatch.setattr(territories_logic, "get_normatives_values_by_parent_id_from_db", by_parent)
    group = next(group for group in MCP_GROUPS if group.name == "territories")
    server = FastMCP("Normatives test")
    server.mount(group.router)
    return SimpleNamespace(server=server, connection=connection, by_territory=by_territory, by_parent=by_parent)


@pytest.mark.asyncio
async def test_normative_tools_are_exposed_only_in_territories():
    for group in MCP_GROUPS:
        server = FastMCP(group.name)
        server.mount(group.router)
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
        if group.name != "territories":
            assert TOOL_NAMES.isdisjoint(tools)
            continue

        assert TOOL_NAMES <= tools.keys()
        for name in TOOL_NAMES:
            tool = tools[name]
            assert tool.annotations.readOnlyHint is True
            assert "territories" in tool.meta["fastmcp"]["tags"]
            assert tool.outputSchema
            properties = tool.inputSchema["properties"]
            assert "request" not in properties
            assert "meta" not in properties
            assert all(prop.get("description") for prop in properties.values())
        assert tools["GetTerritoryNormatives"].inputSchema["required"] == ["territory_id"]
        assert not tools["GetNormativesValuesGeoJSON"].inputSchema.get("required")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"territory_id": 2}, (2, None, False, False, False)),
        ({"territory_id": 2, "year": 2024}, (2, 2024, False, False, False)),
        (
            {"territory_id": 2, "last_only": True, "include_child_territories": True, "cities_only": True},
            (2, None, True, True, True),
        ),
    ],
)
async def test_territory_normatives_call_business_logic(mcp_backend, normative, arguments, expected):
    mcp_backend.by_territory.return_value = [normative]
    async with Client(mcp_backend.server) as client:
        result = await client.call_tool("GetTerritoryNormatives", arguments)
    mcp_backend.by_territory.assert_awaited_once_with(mcp_backend.connection, *expected)
    assert result.structured_content["result"] == [
        {
            "service_type": {"id": 1, "name": "School"},
            "urban_function": None,
            "year": 2024,
            "territory": {"id": 2, "name": "City"},
            "radius_availability_meters": 500,
            "time_availability_minutes": None,
            "services_per_1000_normative": 2,
            "services_capacity_per_1000_normative": None,
            "normative_type": "parent",
            "is_regulated": True,
            "source": "Regional standard",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("centers_only", [False, True])
async def test_normative_values_geojson(mcp_backend, normative, centers_only):
    mcp_backend.by_parent.return_value = [
        TerritoryWithNormativesDTO(
            territory_id=2,
            name="City",
            territory_type_id=3,
            territory_type_name="Municipality",
            is_city=True,
            geometry=Polygon([(0, 0), (2, 0), (2, 2), (0, 0)]),
            centre_point=Point(1, 1),
            normatives=[normative],
        )
    ]
    async with Client(mcp_backend.server) as client:
        result = await client.call_tool(
            "GetNormativesValuesGeoJSON", {"parent_id": 1, "year": 2024, "centers_only": centers_only}
        )
    mcp_backend.by_parent.assert_awaited_once_with(mcp_backend.connection, 1, 2024, False)
    data = result.structured_content
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    feature = data["features"][0]
    assert feature["geometry"]["type"] == ("Point" if centers_only else "Polygon")
    properties = feature["properties"]
    assert properties["territory_id"] == 2
    assert properties["centre_point"] == {"type": "Point", "coordinates": [1.0, 1.0]}
    assert properties["territory_type"] == {"id": 3, "name": "Municipality"}
    assert properties["normatives"][0]["name"] == "School"
    assert properties["normatives"][0]["normative_type"] == "parent"
    assert properties["normatives"][0]["radius_availability_meters"] == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("last_only", [False, True])
async def test_top_level_normative_values_and_empty_results(mcp_backend, last_only):
    async with Client(mcp_backend.server) as client:
        values = await client.call_tool("GetNormativesValuesGeoJSON", {"last_only": last_only})
        normatives = await client.call_tool("GetTerritoryNormatives", {"territory_id": 2})
    mcp_backend.by_parent.assert_awaited_once_with(mcp_backend.connection, None, None, last_only)
    assert values.structured_content == {"type": "FeatureCollection", "features": []}
    assert normatives.structured_content == {"result": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name, arguments, message",
    [
        ("GetTerritoryNormatives", {"territory_id": 2, "year": 2024, "last_only": True}, "year"),
        ("GetNormativesValuesGeoJSON", {"year": 2024, "last_only": True}, "year"),
        ("GetTerritoryNormatives", {"territory_id": 2, "cities_only": True}, "include_child_territories"),
        ("GetTerritoryNormatives", {"territory_id": 0}, "greater than 0"),
        ("GetNormativesValuesGeoJSON", {"parent_id": -1}, "greater than 0"),
        ("GetTerritoryNormatives", {}, "territory_id"),
    ],
)
async def test_invalid_arguments_do_not_reach_database(mcp_backend, tool_name, arguments, message):
    async with Client(mcp_backend.server) as client:
        result = await client.call_tool(tool_name, arguments, raise_on_error=False)
    assert result.is_error
    assert message in result.content[0].text
    mcp_backend.by_territory.assert_not_awaited()
    mcp_backend.by_parent.assert_not_awaited()
