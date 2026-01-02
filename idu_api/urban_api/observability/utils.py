"""Observability-related utility functions and classes are located here."""

import re
from collections import defaultdict

import fastapi
import structlog
from opentelemetry import trace


class URLsMapper:
    """Helper to change URL from given regex pattern to the given static value.

    For example, with map {"GET": {"/api/debug/.*": "/api/debug/*"}} all GET-requests with URL
    starting with "/api/debug/" will be placed in path "/api/debug/*" in metrics.
    """

    def __init__(self, urls_map: dict[str, dict[str, str]] | None = None):
        self._map: dict[str, dict[re.Pattern, str]] = defaultdict(dict)
        """[method -> [pattern -> mapped_to]]"""

        if urls_map is not None:
            for method, patterns in urls_map.items():
                for pattern, value in patterns.items():
                    self.add(method, pattern, value)

    def add(self, method: str, pattern: str, mapped_to: str) -> None:
        """Add entry to the map. If pattern compilation is failed, ValueError is raised."""
        regexp = re.compile(pattern)
        self._map[method.upper()][regexp] = mapped_to

    def add_routes(self, routes: list[fastapi.routing.APIRoute]) -> None:
        """Add full route regexes to the map."""
        logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)
        for route in routes:
            if not hasattr(route, "path_regex") or not hasattr(route, "path"):
                logger.warning("route has no 'path_regex' or 'path' attribute", route=route)
                continue
            if "{" not in route.path:  # ignore simple routes
                continue
            route_path = route.path
            while "{" in route_path:
                lbrace = route_path.index("{")
                rbrace = route_path.index("}", lbrace + 1)
                route_path = route_path[:lbrace] + "*" + route_path[rbrace + 1 :]
            for method in route.methods:
                self._map[method.upper()][route.path_regex] = route_path

    def map(self, method: str, url: str) -> str:
        """Check every map entry with `re.match` and return matched value. If not found, return original string."""
        for regexp, mapped_to in self._map[method.upper()].items():
            if regexp.match(url) is not None:
                return mapped_to
        return url


def get_tracing_headers() -> dict[str, str]:
    ctx = trace.get_current_span().get_span_context()
    if ctx.trace_id == 0:
        return {}
    return {
        "X-Span-Id": format(ctx.span_id, "016x"),
        "X-Trace-Id": format(ctx.trace_id, "032x"),
    }
