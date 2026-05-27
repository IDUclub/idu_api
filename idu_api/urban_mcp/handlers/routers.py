"""MCP routers (sub-apps) for different resource groups."""

from fastmcp import FastMCP

from idu_api.urban_mcp.dependencies.auth_dep import AnyTokenVerifier

projects_mcp = FastMCP(
    name="projects",
    auth=AnyTokenVerifier(),
)
"""Tools for user projects, scenarios, scenario objects and project-specific data."""

territories_mcp = FastMCP(
    name="territories",
    auth=AnyTokenVerifier(),
)
"""Tools for base territorial data, reference urban objects and public territory composition."""

physical_objects_mcp = FastMCP(
    name="physical_objects",
    auth=AnyTokenVerifier(),
)
"""Tools for physical objects."""

dictionaries_mcp = FastMCP(
    name="dictionaries",
    auth=AnyTokenVerifier(),
)
"""Tools for object types, service types, territory types, zone types and other dictionaries."""

indicators_mcp = FastMCP(
    name="indicators",
    auth=AnyTokenVerifier(),
)
"""Tools for territory and scenario indicators."""

soc_groups_mcp = FastMCP(
    name="soc_groups",
    auth=AnyTokenVerifier(),
)
"""Tools gor social groups and social values."""

routers_list = [
    projects_mcp,
    territories_mcp,
    dictionaries_mcp,
    indicators_mcp,
    physical_objects_mcp,
    soc_groups_mcp,
]

__all__ = ["routers_list"]
