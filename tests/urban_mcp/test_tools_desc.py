import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastmcp import Client

from tests.urban_mcp.test_simple import GROUP_PATHS, TEST_CASES, ToolCase, make_client


@dataclass(frozen=True)
class SchemaIssue:
    group: str
    tool: str
    message: str

    def __str__(self) -> str:
        return f"{self.group}/{self.tool}: {self.message}"


def to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True)
    if hasattr(value, "dict"):
        return value.dict(by_alias=True)
    return {}


def get_tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", ""))
    return str(getattr(tool, "name", ""))


def get_input_schema(tool: Any) -> dict[str, Any]:
    if isinstance(tool, dict):
        return to_plain_dict(tool.get("inputSchema") or tool.get("input_schema"))
    return to_plain_dict(getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None))


def get_tool_description(tool: Any) -> str | None:
    if isinstance(tool, dict):
        return tool.get("description")
    return getattr(tool, "description", None)


def get_type_repr(schema: dict[str, Any]) -> str:
    if "type" in schema:
        return str(schema["type"])
    if "anyOf" in schema:
        return " | ".join(get_type_repr(item) for item in schema["anyOf"])
    if "oneOf" in schema:
        return " | ".join(get_type_repr(item) for item in schema["oneOf"])
    if "$ref" in schema:
        return str(schema["$ref"])
    return "<unspecified>"


def format_params(schema: dict[str, Any]) -> list[str]:
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])

    lines: list[str] = []
    for name in sorted(properties):
        prop_schema = to_plain_dict(properties[name])
        marker = "required" if name in required else "optional"
        description = prop_schema.get("description") or prop_schema.get("title") or ""
        lines.append(f"{name}: {get_type_repr(prop_schema)} ({marker}) {description}".rstrip())

    return lines


def validate_schema(group: str, tool_name: str, tool: Any) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    schema = get_input_schema(tool)

    if not schema:
        return [SchemaIssue(group, tool_name, "inputSchema is missing or empty")]

    if schema.get("type") != "object":
        issues.append(SchemaIssue(group, tool_name, "inputSchema.type must be object"))

    properties = schema.get("properties")
    if properties is None:
        issues.append(SchemaIssue(group, tool_name, "inputSchema.properties is missing"))
    elif not isinstance(properties, dict):
        issues.append(SchemaIssue(group, tool_name, "inputSchema.properties must be an object"))

    required = schema.get("required", [])
    if required is not None and not isinstance(required, list):
        issues.append(SchemaIssue(group, tool_name, "inputSchema.required must be a list"))

    if "meta" in (properties or {}):
        issues.append(SchemaIssue(group, tool_name, "inputSchema must not expose meta as an argument"))

    description = get_tool_description(tool)
    if not description:
        issues.append(SchemaIssue(group, tool_name, "tool description is missing"))

    for param_name, param_schema in (properties or {}).items():
        param_schema = to_plain_dict(param_schema)
        if not param_schema:
            issues.append(SchemaIssue(group, tool_name, f"{param_name}: empty parameter schema"))
            continue
        has_type_marker = any(marker in param_schema for marker in ("type", "anyOf", "oneOf", "$ref"))
        if not has_type_marker:
            issues.append(SchemaIssue(group, tool_name, f"{param_name}: type/anyOf/oneOf/$ref is missing"))
        if "description" not in param_schema and "title" not in param_schema:
            issues.append(SchemaIssue(group, tool_name, f"{param_name}: description/title is missing"))

    return issues


def validate_case_against_schema(case: ToolCase, schema: dict[str, Any]) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    arguments = case.arguments or {}

    for arg_name in arguments:
        if arg_name not in properties:
            issues.append(
                SchemaIssue(case.group, case.name, f"test argument '{arg_name}' is not present in inputSchema")
            )

    for required_name in required:
        if required_name not in arguments and case.skip_reason is None:
            issues.append(
                SchemaIssue(case.group, case.name, f"required argument '{required_name}' is absent in ToolCase")
            )

    if case.meta:
        issues.append(
            SchemaIssue(case.group, case.name, "ToolCase still uses meta; pass identifiers through arguments")
        )

    return issues


async def inspect_group(group: str, dump_schema: bool, tool_filter: set[str] | None) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    client: Client = make_client(group)
    expected_cases = [case for case in TEST_CASES if case.group == group]
    expected_by_name = {case.name: case for case in expected_cases}

    async with client:
        tools = await client.list_tools()

    tools_by_name = {get_tool_name(tool): tool for tool in tools}
    tools_by_name.pop("", None)

    if tool_filter:
        tools_by_name = {name: tool for name, tool in tools_by_name.items() if name in tool_filter}

    print(f"\n=== {group} ===")
    print(f"Tools returned by list_tools: {len(tools_by_name)}")

    for tool_name in sorted(tools_by_name):
        tool = tools_by_name[tool_name]
        schema = get_input_schema(tool)
        issues.extend(validate_schema(group, tool_name, tool))

        case = expected_by_name.get(tool_name)
        if case is not None:
            issues.extend(validate_case_against_schema(case, schema))

        print(f"\n--- {tool_name} ---")
        print("required:", ", ".join(schema.get("required") or []) or "<none>")
        print("parameters:")
        for line in format_params(schema):
            print(f"- {line}")
        if dump_schema:
            print("inputSchema:")
            print(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True))

    if not tool_filter:
        missing_from_server = sorted(set(expected_by_name) - set(tools_by_name))
        for tool_name in missing_from_server:
            issues.append(SchemaIssue(group, tool_name, "ToolCase exists, but list_tools did not return this tool"))
    else:
        missing_requested_tools = sorted(tool_filter - set(tools_by_name))
        for tool_name in missing_requested_tools:
            issues.append(SchemaIssue(group, tool_name, "requested by --tool, but list_tools did not return this tool"))

    return issues


async def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Urban MCP tools inputSchema and argument declarations.")
    parser.add_argument("--group", choices=sorted(GROUP_PATHS), help="Check only one MCP group.")
    parser.add_argument("--tool", action="append", help="Check only selected tool name. Can be passed multiple times.")
    parser.add_argument("--dump-schema", action="store_true", help="Print full inputSchema JSON for every tool.")
    args = parser.parse_args()

    groups = [args.group] if args.group else list(GROUP_PATHS)
    tool_filter = set(args.tool) if args.tool else None

    issues: list[SchemaIssue] = []
    for group in groups:
        issues.extend(await inspect_group(group, args.dump_schema, tool_filter))

    print("\n=== SUMMARY ===")
    if not issues:
        print("OK: all inspected tool schemas look consistent.")
        return 0

    print(f"Issues: {len(issues)}")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
