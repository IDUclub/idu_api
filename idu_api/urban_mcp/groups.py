"""Urban MCP tool groups.

This module defines thematic MCP groups. Each group contains only the routers
that should be exposed to a client through a specific MCP endpoint.
"""

from dataclasses import dataclass

from fastmcp import FastMCP

from idu_api.urban_mcp.handlers.routers import (
    dictionaries_mcp,
    indicators_mcp,
    physical_objects_mcp,
    projects_mcp,
    soc_groups_mcp,
    territories_mcp,
)


@dataclass(frozen=True)
class MCPGroup:
    """Description of a thematic MCP tool group."""

    name: str
    path: str
    description: str
    router: FastMCP


MCP_GROUPS: list[MCPGroup] = [
    MCPGroup(
        name="projects",
        path="/mcp/projects",
        description=(
            "Инструменты для работы с проектами, сценариями, проектными территориями "
            "и объектами внутри пользовательских сценариев. Позволяют получить данные "
            "по проекту и сценариям, а также создать проект."
        ),
        router=projects_mcp,
    ),
    MCPGroup(
        name="territories",
        path="/mcp/territories",
        description=(
            "Инструменты для работы с территориями, базовыми городскими "
            "объектами и данными, находящимися на территориях."
        ),
        router=territories_mcp,
    ),
    MCPGroup(
        name="physical_objects",
        path="/mcp/physical_objects",
        description=(
            "Инструменты для работы с физическими объектами: включает получение "
            "сервисов, расположенных внутри объекта, а также его геометрий."
        ),
        router=physical_objects_mcp,
    ),
    MCPGroup(
        name="dictionaries",
        path="/mcp/dictionaries",
        description=(
            "Инструменты для получения справочников: типы территорий, физических объектов, "
            "сервисов, показателей и других справочных сущностей."
        ),
        router=dictionaries_mcp,
    ),
    MCPGroup(
        name="indicators",
        path="/mcp/indicators",
        description=("Инструменты для получения показателей территорий, проектов и сценариев."),
        router=indicators_mcp,
    ),
    MCPGroup(
        name="soc_groups",
        path="/mcp/soc_groups",
        description=(
            "Инструменты для работы с социальными группами, социальными ценностями " "и связанными с ними данными."
        ),
        router=soc_groups_mcp,
    ),
]
