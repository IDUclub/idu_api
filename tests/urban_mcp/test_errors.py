"""Keep validation and mapped error contracts across MCP SDK upgrades."""

import pytest
from fastmcp.exceptions import McpError

from idu_api.urban_mcp.exceptions.logic.mapper import _get_mcp_error as logic_error
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper
from idu_api.urban_mcp.exceptions.services.mapper import _get_mcp_error as service_error
from idu_api.urban_mcp.handlers import indicators, physical_objects, services, territories


@pytest.mark.parametrize(
    "validate,args,message_part",
    [
        (territories._parse_ids, ("invalid",), "territories_ids"),
        (territories._validate_levels, (False, True), "cities_only"),
        (territories._validate_normatives_year, (2024, True), "year"),
        (services._parse_ids, ("invalid",), "ids"),
        (services._validate_child_territories, (False, True), "cities_only"),
        (services._validate_service_type_or_function, (1, 2), "service_type_id"),
        (physical_objects._parse_ids, ("invalid",), "ids"),
        (physical_objects._validate_child_territories, (False, True), "cities_only"),
        (physical_objects._validate_type_or_function, (1, 2), "physical_object_type_id"),
        (indicators._parse_indicator_ids, ("invalid",), "indicator"),
    ],
)
def test_invalid_filters_keep_protocol_error(validate, args, message_part):
    with pytest.raises(McpError) as caught:
        validate(*args)
    assert caught.value.error.code == -32602
    assert message_part in caught.value.error.message


@pytest.mark.parametrize("make_error", [logic_error, service_error])
def test_domain_error_factories_preserve_code_and_message(make_error):
    error = make_error(-32001, "Missing territory")
    assert error.error.code == -32001
    assert error.error.message == "Missing territory"


def test_registered_exception_preserves_error_details():
    mapper = ExceptionMapper()
    mapper.register_simple(ValueError, -32602, "Invalid filter")

    error = mapper.apply(ValueError("bad input"))

    assert error.error.code == -32602
    assert error.error.message == "Invalid filter"
    assert error.error.data == {"error_type": "ValueError", "error": "bad input"}


def test_unknown_exception_keeps_internal_details_private():
    error = ExceptionMapper().apply(RuntimeError("private details"))
    assert error.error.code == -32603
    assert error.error.message == "Internal error"
    assert error.error.data is None
