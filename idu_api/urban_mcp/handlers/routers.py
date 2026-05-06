"""MCP routers (sub-apps) for different resource groups."""

from fastmcp import FastMCP

from idu_api.urban_mcp.dependencies.auth_dep import AnyTokenVerifier

buffers_mcp = FastMCP(name="buffers", auth=AnyTokenVerifier())
functional_zones_mcp = FastMCP(name="functional_zones", auth=AnyTokenVerifier())
indicators_mcp = FastMCP(name="indicators", auth=AnyTokenVerifier())
object_geometries_mcp = FastMCP(name="object_geometries", auth=AnyTokenVerifier())
physical_objects_mcp = FastMCP(name="physical_objects", auth=AnyTokenVerifier())
projects_scenarios_mcp = FastMCP(name="projects", auth=AnyTokenVerifier())
services_mcp = FastMCP(name="services", auth=AnyTokenVerifier())
soc_groups_mcp = FastMCP(name="soc_groups", auth=AnyTokenVerifier())
territories_mcp = FastMCP(name="territories", auth=AnyTokenVerifier())
urban_objects_mcp = FastMCP(name="urban_objects", auth=AnyTokenVerifier())

routers_list = [
    buffers_mcp,
    functional_zones_mcp,
    indicators_mcp,
    object_geometries_mcp,
    physical_objects_mcp,
    projects_scenarios_mcp,
    services_mcp,
    soc_groups_mcp,
    territories_mcp,
    urban_objects_mcp,
]

__all__ = ["routers_list"]
