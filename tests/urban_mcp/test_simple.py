import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from fastmcp import Client

MCP_URL = "http://localhost:8000"
TOKEN = "access token"
GROUP_PATHS: dict[str, str] = {
    "projects": "/mcp/projects",
    "territories": "/mcp/territories",
    "physical_objects": "/mcp/physical_objects",
    "dictionaries": "/mcp/dictionaries",
    "indicators": "/mcp/indicators",
    "soc_groups": "/mcp/soc_groups",
}


def make_client(group: str) -> Client:
    url = f"{MCP_URL}{GROUP_PATHS[group]}"
    if TOKEN:
        return Client(url, auth=TOKEN)
    return Client(url)


@dataclass
class ToolCase:
    group: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] | None = None
    title: str | None = None
    skip_reason: str | None = None


TEST_CASES: list[ToolCase] = [
    # --- dictionaries ---
    ToolCase("dictionaries", "GetBufferTypes"),
    ToolCase("dictionaries", "GetDefaultBufferValues"),
    ToolCase(
        "dictionaries",
        "GetFunctionalZoneSources",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "dictionaries",
        "GetScenarioFunctionalZoneSources",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "dictionaries",
        "GetContextFunctionalZoneSources",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase("dictionaries", "GetMeasurementUnits"),
    ToolCase("dictionaries", "GetIndicatorsGroups"),
    ToolCase(
        "dictionaries",
        "GetPhysicalObjectTypes",
        arguments={},
    ),
    ToolCase(
        "dictionaries",
        "GetPhysicalObjectFunctionsByParent",
        arguments={
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "dictionaries",
        "GetPhysicalObjectTypesHierarchy",
        arguments={},
    ),
    ToolCase(
        "dictionaries",
        "GetServiceTypesByPhysicalObjectType",
        arguments={
            "physical_object_type_id": 4,
        },
    ),
    ToolCase(
        "dictionaries",
        "GetServiceTypes",
        arguments={},
    ),
    ToolCase(
        "dictionaries",
        "GetUrbanFunctionsByParent",
        arguments={
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "dictionaries",
        "GetServiceTypesHierarchy",
        arguments={},
    ),
    ToolCase(
        "dictionaries",
        "GetPhysicalObjectTypesByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase("dictionaries", "GetTerritoryTypes"),
    ToolCase("dictionaries", "GetTargetCityTypes"),
    # --- territories ---
    ToolCase(
        "territories",
        "GetTerritoryBuffersGeoJSON",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "territories",
        "GetFunctionalZonesGeoJSON",
        arguments={
            "territory_id": 13369,
            "year": 2024,
            "source": "OSM",
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "territories",
        "GetPhysicalObjectTypesByTerritoryId",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryPhysicalObjectsGeoJSON",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryPhysicalObjects",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryPhysicalObjectsWithGeometry",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    ToolCase(
        "territories",
        "GetServiceTypesByTerritoryId",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryServicesGeoJSON",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryServicesCapacity",
        arguments={
            "territory_id": 13369,
            "level": 2,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryServices",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryServicesWithGeometry",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryById",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "territories",
        "GetAllTerritoriesGeoJSON",
        arguments={
            "get_all_levels": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "territories",
        "GetAllTerritoriesWithoutGeometry",
        arguments={
            "get_all_levels": False,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoriesWithoutGeometryHierarchy",
        arguments={
            "ordering": "asc",
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoriesByIdsGeoJSON",
        arguments={
            "territories_ids": "13369",
            "centers_only": True,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoryNormatives",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "include_child_territories": False,
        },
    ),
    ToolCase(
        "territories",
        "GetNormativesValuesGeoJSON",
        arguments={
            "parent_id": 13369,
            "last_only": True,
            "centers_only": True,
        },
    ),
    ToolCase(
        "territories",
        "GetTerritories",
        arguments={
            "get_all_levels": False,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "territories",
        "GetTerritoriesWithoutGeometry",
        arguments={
            "parent_id": None,
            "get_all_levels": True,
            "ordering": "asc",
        },
    ),
    # --- indicators ---
    ToolCase(
        "indicators",
        "GetIndicatorsByGroupId",
        arguments={
            "indicators_group_id": 1,
        },
    ),
    ToolCase(
        "indicators",
        "GetIndicatorsByParent",
        arguments={
            "parent_id": None,
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "indicators",
        "GetIndicatorsByTerritoryId",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "indicators",
        "GetTerritoryIndicatorValuesGeoJSON",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "centers_only": True,
        },
    ),
    ToolCase(
        "indicators",
        "GetTerritoryIndicatorValues",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "include_child_territories": False,
            "cities_only": False,
        },
    ),
    ToolCase(
        "indicators",
        "GetIndicatorValuesByParentTerritory",
        arguments={
            "parent_id": 13369,
            "last_only": True,
            "with_binned": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "indicators",
        "GetScenarioIndicatorsValues",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "indicators",
        "GetScenarioHexagonsWithIndicatorsValues",
        arguments={
            "scenario_id": 124,
            "centers_only": True,
        },
    ),
    # --- physical objects ---
    ToolCase(
        "physical_objects",
        "GetPhysicalObjectById",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "physical_objects",
        "GetServicesByPhysicalObjectId",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "physical_objects",
        "GetServicesWithGeometryByPhysicalObjectId",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "physical_objects",
        "GetPhysicalObjectGeometries",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    # --- projects ---
    ToolCase(
        "projects",
        "GetScenarioBuffers",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetContextBuffers",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioFunctionalZones",
        arguments={
            "scenario_id": 124,
            "year": 2024,
            "source": "OSM",
        },
    ),
    ToolCase(
        "projects",
        "GetContextFunctionalZones",
        arguments={
            "scenario_id": 124,
            "year": 2024,
            "source": "OSM",
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjectTypes",
        arguments={
            "scenario_id": 124,
            "for_context": False,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjects",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjectsWithGeometry",
        arguments={
            "scenario_id": 124,
            "centers_only": True,
        },
    ),
    ToolCase(
        "projects",
        "GetContextPhysicalObjects",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetContextPhysicalObjectsWithGeometry",
        arguments={
            "scenario_id": 124,
            "include_scenario_objects": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "projects",
        "GetProjectById",
        arguments={
            "project_id": 1,
        },
    ),
    ToolCase(
        "projects",
        "CreateProject",
        arguments={
            "project": {
                "name": "MCP smoke test project",
                "territory_id": 13369,
                "is_city": True,
                "description": "Created by tests/urban_mcp/test_simple.py",
                "public": False,
                "properties": {},
                "is_regional": True,
            }
        },
        skip_reason="mutating tool; enable manually when project creation should be tested",
    ),
    ToolCase(
        "projects",
        "GetProjectTerritoryByProjectId",
        arguments={
            "project_id": 1,
        },
    ),
    ToolCase(
        "projects",
        "GetProjectPhasesByProjectId",
        arguments={
            "project_id": 1,
        },
    ),
    ToolCase(
        "projects",
        "GetProjectCadastresByProjectId",
        arguments={
            "project_id": 1,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioById",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioServiceTypes",
        arguments={
            "scenario_id": 124,
            "for_context": False,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioServices",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetScenarioServicesWithGeometry",
        arguments={
            "scenario_id": 124,
            "centers_only": True,
        },
    ),
    ToolCase(
        "projects",
        "GetContextServices",
        arguments={
            "scenario_id": 124,
        },
    ),
    ToolCase(
        "projects",
        "GetContextServicesWithGeometry",
        arguments={
            "scenario_id": 124,
            "include_scenario_objects": False,
            "centers_only": True,
        },
    ),
    # --- social groups / social values ---
    ToolCase(
        "soc_groups",
        "GetSocialValuesByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase(
        "soc_groups",
        "GetSocialGroupsByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase("soc_groups", "GetSocialGroups"),
    ToolCase(
        "soc_groups",
        "GetSocialGroupById",
        arguments={
            "soc_group_id": 1,
        },
    ),
    ToolCase("soc_groups", "GetSocialValues"),
    ToolCase(
        "soc_groups",
        "GetSocialValueById",
        arguments={
            "soc_value_id": 1,
        },
    ),
    ToolCase(
        "soc_groups",
        "GetServiceTypesBySocialValueId",
        arguments={
            "soc_value_id": 1,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "soc_groups",
        "GetSocialValueIndicatorValues",
        arguments={
            "soc_value_id": 1,
            "territory_id": 13369,
            "last_only": True,
        },
    ),
]


def short_repr(value: Any, limit: int = 1200) -> str:
    text = repr(value)
    if len(text) > limit:
        return text[:limit] + "... <truncated>"
    return text


async def safe_call_tool(client: Client, case: ToolCase) -> tuple[str, bool | None, Any]:
    title = case.title or f"{case.group}/{case.name}"
    print(f"\n--- {title} ---")
    print("arguments:", json.dumps(case.arguments, ensure_ascii=False))
    if case.meta is not None:
        print("meta:", json.dumps(case.meta, ensure_ascii=False))
    if case.skip_reason is not None:
        print("SKIP:", case.skip_reason)
        return f"{case.group}/{case.name}", None, case.skip_reason

    try:
        result = await client.call_tool(
            case.name,
            arguments=case.arguments,
            meta=case.meta,
        )
        print("OK")
        print(short_repr(result))
        return f"{case.group}/{case.name}", True, result
    except Exception as exc:
        print("ERROR:", repr(exc))
        return f"{case.group}/{case.name}", False, exc


def extract_tool_names(tools: Any) -> set[str]:
    names: set[str] = set()

    for tool in tools:
        name = getattr(tool, "name", None)
        if name is None and isinstance(tool, dict):
            name = tool.get("name")
        if name:
            names.add(name)

    return names


async def main() -> None:
    results: list[tuple[str, bool | None, Any]] = []

    cases_by_group: dict[str, list[ToolCase]] = {group: [] for group in GROUP_PATHS}
    for case in TEST_CASES:
        cases_by_group.setdefault(case.group, []).append(case)

    for group, path in GROUP_PATHS.items():
        client = make_client(group)

        async with client:
            print(f"\n=== {group} ({path}) ===")
            print("--- ping ---")
            try:
                await client.ping()
                print("OK")
            except Exception as exc:
                print("ERROR:", repr(exc))

            print("\n--- list_tools ---")
            tools = await client.list_tools()
            available_tool_names = extract_tool_names(tools)
            print(f"Found tools: {len(available_tool_names)}")
            for name in sorted(available_tool_names):
                print("-", name)

            tested_tool_names = {case.name for case in cases_by_group[group]}
            missing_cases = sorted(available_tool_names - tested_tool_names)
            unknown_cases = sorted(tested_tool_names - available_tool_names)

            if missing_cases:
                print("\nTools without test cases:")
                for name in missing_cases:
                    print("-", name)

            if unknown_cases:
                print("\nTest cases for tools not returned by list_tools:")
                for name in unknown_cases:
                    print("-", name)

            for case in cases_by_group[group]:
                results.append(await safe_call_tool(client, case))

    passed = sum(1 for _, ok, _ in results if ok is True)
    skipped = sum(1 for _, ok, _ in results if ok is None)
    failed = sum(1 for _, ok, _ in results if ok is False)

    print("\n=== SUMMARY ===")
    print(f"Passed: {passed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Total:  {len(results)}")

    if failed:
        print("\nFailed tools:")
        for name, ok, error in results:
            if ok is False:
                print(f"- {name}: {repr(error)}")


if __name__ == "__main__":
    asyncio.run(main())
