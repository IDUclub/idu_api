import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from fastmcp import Client

MCP_URL = "http://localhost:8002/mcp"
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJadlA1TzV5R1NzVGwtN3FZXzlGUU5vam5CWkx5bWUwcG5WMGF5UzZHU2MwIn0.eyJleHAiOjE3Nzk4ODg3MzQsImlhdCI6MTc3OTg4ODQzNCwiYXV0aF90aW1lIjoxNzc5ODg4NDIyLCJqdGkiOiJvbnJ0YWM6NmJkOTY1NTktZmVmMi02MjJjLWVhY2EtNGYwYTI4NDlhNzNiIiwiaXNzIjoiaHR0cHM6Ly9rZXljbG9hay5pZHUuYWN0Y29nbml0aXZlLm9yZy9yZWFsbXMvSURVIiwiYXVkIjpbInVyYmFuLWFwaSIsImFjY291bnQiXSwic3ViIjoiMzk1MWE0ZTgtZGU3ZS00Zjc0LTljNzItNmZhNTE5ZGNmYmJmIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoidXJiYW4tYXBpLXN3YWdnZXIiLCJzaWQiOiJnNTUtRDNPUDNMTFYybmdRQlhhOTRUYVoiLCJhY3IiOiIwIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xMC4zMi4xLjQ3OjUzMDAiLCIqIiwiaHR0cHM6Ly91cmJhbi1hcGkuaWR1bGFiLnJ1IiwiaHR0cHM6Ly91cmJhbi1hcGkudGVzdGluZy5pZHVsYWIucnUiLCJodHRwOi8vMTAuMzIuMS42NTo1MzAwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLWlkdSIsIm9mZmxpbmVfYWNjZXNzIiwiU1RBRkYiLCJBRE1JTiIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsidXJiYW4tYXBpIjp7InJvbGVzIjpbImxvYWRlci5pbmRpY2F0b3JzIiwibG9hZGVyLnRlcnJpdG9yaWVzIiwibG9hZGVyLm5vcm1hdGl2ZXMiLCJsb2FkZXIuc2VydmljZXMiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5hbWUiOiJBZG1pbiBUZXN0IiwicHJlZmVycmVkX3VzZXJuYW1lIjoiYWRtaW5AdGVzdC5ydSIsImdpdmVuX25hbWUiOiJBZG1pbiIsImZhbWlseV9uYW1lIjoiVGVzdCIsImVtYWlsIjoiYWRtaW5AdGVzdC5ydSJ9.PzYP4QI1y1-ipl7B8Z-jIJ-EgQxEf1mDzjDJ-AefkIZkI3iWAjuHOHyt7yCsnOTRwVwBw6gqf7kM0pfDPdsD042Df78ZTnFkICgQsKQb1QU43FvfitBw7EKzcul4DLqZxHrpDxIti00ozZ_cHkoV5mv9kHHOgFo5oyrUkeD2hiXYKki-NoCRgonHirl7vxkZO2-g-U3BUVjzARSMAtr9nbpzZNznUFEj34Yf9N6T58UIdFhPMeyrBFjmDBqvzevV7QK1P0B69sbeYe3yH1gnuAc_ayJStouv5c9zDm6GwJU97nc1tfDaH9tVXKOZ6cq9gYrnCG08Yj2rAMq-14KuQg"
GROUP_PATHS: dict[str, str] = {
    "projects": "/projects",
    "territories": "/territories",
    "physical_objects": "/physical_objects",
    "dictionaries": "/dictionaries",
    "indicators": "/indicators",
    "soc_groups": "/soc_groups",
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
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "dictionaries",
        "GetContextFunctionalZoneSources",
        arguments={},
        meta={"scenario_id": "124"},
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
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "indicators",
        "GetScenarioHexagonsWithIndicatorsValues",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
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
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextBuffers",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioFunctionalZones",
        arguments={
            "year": 2024,
            "source": "OSM",
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextFunctionalZones",
        arguments={
            "year": 2024,
            "source": "OSM",
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjectTypes",
        arguments={
            "for_context": False,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjects",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioPhysicalObjectsWithGeometry",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextPhysicalObjects",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextPhysicalObjectsWithGeometry",
        arguments={
            "include_scenario_objects": False,
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetProjectById",
        arguments={},
        meta={"project_id": "1"},
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
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "projects",
        "GetProjectPhasesByProjectId",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "projects",
        "GetProjectCadastresByProjectId",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "projects",
        "GetScenarioById",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioServiceTypes",
        arguments={
            "for_context": False,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioServices",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetScenarioServicesWithGeometry",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextServices",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "projects",
        "GetContextServicesWithGeometry",
        arguments={
            "include_scenario_objects": False,
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
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
