import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from fastmcp import Client

MCP_URL = "http://localhost:8001/mcp"
TOKEN = "your_access_token"
client = Client(MCP_URL, auth=TOKEN)


@dataclass
class ToolCase:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] | None = None
    title: str | None = None


TEST_CASES: list[ToolCase] = [
    # --- buffers ---
    ToolCase("GetBufferTypes"),
    ToolCase("GetDefaultBufferValues"),
    ToolCase(
        "GetTerritoryBuffersGeoJSON",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "GetScenarioBuffers",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextBuffers",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    # --- functional zones ---
    ToolCase(
        "GetFunctionalZoneSources",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "GetFunctionalZones",
        arguments={
            "territory_id": 13369,
            "year": 2024,
            "source": "OSM",
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
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
        "GetScenarioFunctionalZoneSources",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioFunctionalZones",
        arguments={
            "year": 2024,
            "source": "OSM",
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextFunctionalZoneSources",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextFunctionalZones",
        arguments={
            "year": 2024,
            "source": "OSM",
        },
        meta={"scenario_id": "124"},
    ),
    # --- indicators ---
    ToolCase("GetMeasurementUnits"),
    ToolCase("GetIndicatorsGroups"),
    ToolCase(
        "GetIndicatorsByGroupId",
        arguments={
            "indicators_group_id": 1,
        },
    ),
    ToolCase(
        "GetIndicatorsByParent",
        arguments={
            "parent_id": None,
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "GetIndicatorById",
        arguments={
            "indicator_id": 1,
        },
    ),
    ToolCase(
        "GetIndicatorValueById",
        arguments={
            "indicator_value_id": 1,
        },
    ),
    ToolCase(
        "GetIndicatorValuesByIndicatorId",
        arguments={
            "indicator_id": 1,
        },
    ),
    ToolCase(
        "GetIndicatorsByTerritoryId",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "GetTerritoryIndicatorValuesGeoJSON",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "centers_only": True,
        },
    ),
    ToolCase(
        "GetTerritoryIndicatorValues",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "include_child_territories": False,
            "cities_only": False,
        },
    ),
    ToolCase(
        "GetIndicatorValuesByParentTerritory",
        arguments={
            "parent_id": 13369,
            "last_only": True,
            "with_binned": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "GetScenarioIndicatorsValues",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioHexagonsWithIndicatorsValues",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    # --- object geometries ---
    ToolCase(
        "GetObjectGeometriesByIds",
        arguments={
            "object_geometries_ids": "1413139",
        },
    ),
    ToolCase(
        "GetPhysicalObjectsByGeometryId",
        arguments={
            "object_geometry_id": 1413139,
        },
    ),
    ToolCase(
        "GetScenarioGeometries",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioGeometriesWithAllObjects",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextGeometries",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextGeometriesWithAllObjects",
        arguments={
            "include_scenario_objects": False,
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    # --- physical objects ---
    ToolCase(
        "GetPhysicalObjectTypes",
        arguments={},
    ),
    ToolCase(
        "GetPhysicalObjectFunctionsByParent",
        arguments={
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "GetPhysicalObjectTypesHierarchy",
        arguments={},
    ),
    ToolCase(
        "GetServiceTypesByPhysicalObjectType",
        arguments={
            "physical_object_type_id": 4,
        },
    ),
    ToolCase(
        "GetPhysicalObjectById",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "GetServicesByPhysicalObjectId",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "GetServicesWithGeometryByPhysicalObjectId",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "GetPhysicalObjectGeometries",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "GetPhysicalObjectTypesByTerritoryId",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "GetTerritoryPhysicalObjectsGeoJSON",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "GetScenarioPhysicalObjectTypes",
        arguments={
            "for_context": False,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioPhysicalObjects",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioPhysicalObjectsWithGeometry",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextPhysicalObjects",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextPhysicalObjectsWithGeometry",
        arguments={
            "include_scenario_objects": False,
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
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
        "GetTerritoryPhysicalObjectsWithGeometry",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    # --- projects ---
    ToolCase(
        "GetProjectById",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "GetProjectTerritoryByProjectId",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "GetProjectPhasesByProjectId",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "GetProjectCadastresByProjectId",
        arguments={},
        meta={"project_id": "1"},
    ),
    ToolCase(
        "GetScenarioById",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    # --- services ---
    ToolCase(
        "GetServiceTypes",
        arguments={},
    ),
    ToolCase(
        "GetUrbanFunctionsByParent",
        arguments={
            "get_all_subtree": False,
        },
    ),
    ToolCase(
        "GetServiceTypesHierarchy",
        arguments={},
    ),
    ToolCase(
        "GetPhysicalObjectTypesByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase(
        "GetSocialValuesByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase(
        "GetSocialGroupsByServiceType",
        arguments={
            "service_type_id": 1,
        },
    ),
    ToolCase(
        "GetServiceTypesByTerritoryId",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
        },
    ),
    ToolCase(
        "GetTerritoryServicesGeoJSON",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "GetTerritoryServicesCapacity",
        arguments={
            "territory_id": 13369,
            "level": 2,
        },
    ),
    ToolCase(
        "GetScenarioServiceTypes",
        arguments={
            "for_context": False,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioServices",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetScenarioServicesWithGeometry",
        arguments={
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextServices",
        arguments={},
        meta={"scenario_id": "124"},
    ),
    ToolCase(
        "GetContextServicesWithGeometry",
        arguments={
            "include_scenario_objects": False,
            "centers_only": True,
        },
        meta={"scenario_id": "124"},
    ),
    ToolCase(
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
        "GetTerritoryServicesWithGeometry",
        arguments={
            "territory_id": 13369,
            "include_child_territories": True,
            "cities_only": False,
            "ordering": "asc",
            "page_size": 10,
        },
    ),
    # --- social groups / social values ---
    ToolCase("GetSocialGroups"),
    ToolCase(
        "GetSocialGroupById",
        arguments={
            "soc_group_id": 1,
        },
    ),
    ToolCase("GetSocialValues"),
    ToolCase(
        "GetSocialValueById",
        arguments={
            "soc_value_id": 1,
        },
    ),
    ToolCase(
        "GetServiceTypesBySocialValueId",
        arguments={
            "soc_value_id": 1,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "GetSocialValueIndicatorValues",
        arguments={
            "soc_value_id": 1,
            "territory_id": 13369,
            "last_only": True,
        },
    ),
    # --- territories ---
    ToolCase(
        "GetTerritoryById",
        arguments={
            "territory_id": 13369,
        },
    ),
    ToolCase(
        "GetTerritories",
        arguments={
            "get_all_levels": False,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "GetAllTerritoriesGeoJSON",
        arguments={
            "get_all_levels": False,
            "centers_only": True,
        },
    ),
    ToolCase(
        "GetTerritoriesWithoutGeometry",
        arguments={
            "parent_id": None,
            "get_all_levels": True,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "GetAllTerritoriesWithoutGeometry",
        arguments={
            "get_all_levels": False,
            "ordering": "asc",
        },
    ),
    ToolCase(
        "GetTerritoriesWithoutGeometryHierarchy",
        arguments={
            "ordering": "asc",
        },
    ),
    ToolCase(
        "GetTerritoriesByIdsGeoJSON",
        arguments={
            "territories_ids": "13369",
            "centers_only": True,
        },
    ),
    ToolCase("GetTerritoryTypes"),
    ToolCase("GetTargetCityTypes"),
    ToolCase(
        "GetTerritoryNormatives",
        arguments={
            "territory_id": 13369,
            "last_only": True,
            "include_child_territories": False,
        },
    ),
    ToolCase(
        "GetNormativesValuesGeoJSON",
        arguments={
            "parent_id": 13369,
            "last_only": True,
            "centers_only": True,
        },
    ),
    # --- urban objects ---
    ToolCase(
        "GetUrbanObjectById",
        arguments={
            "urban_object_id": 1447450,
        },
    ),
    ToolCase(
        "GetUrbanObjectsByPhysicalObjectId",
        arguments={
            "physical_object_id": 1413142,
        },
    ),
    ToolCase(
        "GetUrbanObjectsByObjectGeometryId",
        arguments={
            "object_geometry_id": 1413139,
        },
    ),
    ToolCase(
        "GetUrbanObjectsByServiceId",
        arguments={
            "service_id": 77291,
        },
    ),
    ToolCase(
        "GetUrbanObjectsByTerritoryId",
        arguments={
            "territory_id": 13369,
        },
    ),
]


def short_repr(value: Any, limit: int = 1200) -> str:
    text = repr(value)
    if len(text) > limit:
        return text[:limit] + "... <truncated>"
    return text


async def safe_call_tool(case: ToolCase) -> tuple[str, bool, Any]:
    title = case.title or case.name
    print(f"\n--- {title} ---")
    print("arguments:", json.dumps(case.arguments, ensure_ascii=False))
    if case.meta is not None:
        print("meta:", json.dumps(case.meta, ensure_ascii=False))

    try:
        result = await client.call_tool(
            case.name,
            arguments=case.arguments,
            meta=case.meta,
        )
        print("OK")
        print(short_repr(result))
        return case.name, True, result
    except Exception as exc:
        print("ERROR:", repr(exc))
        return case.name, False, exc


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
    results: list[tuple[str, bool, Any]] = []

    async with client:
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

        tested_tool_names = {case.name for case in TEST_CASES}
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

        for case in TEST_CASES:
            results.append(await safe_call_tool(case))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    print("\n=== SUMMARY ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {len(results)}")

    if failed:
        print("\nFailed tools:")
        for name, ok, error in results:
            if not ok:
                print(f"- {name}: {repr(error)}")


if __name__ == "__main__":
    asyncio.run(main())
