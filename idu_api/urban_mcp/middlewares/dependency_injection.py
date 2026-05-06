"""Dependency injection middleware is defined here."""

from asyncio import Lock
from typing import Any, Protocol

from fastmcp.resources import ResourceResult
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp import types as mt

from idu_api.common.db.connection.manager import PostgresConnectionManager
from idu_api.urban_api.dependencies import logger_dep


class DependencyInitializer(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for dependency factory callables receiving a DB connection."""

    def __call__(self, conn: PostgresConnectionManager, **kwargs: Any) -> Any: ...


class PassServicesDependenciesMiddleware(Middleware):
    """Construct given service objects with a new Postgres connection from pool.
    Services initializer functions must have database connection as first and only positional argument.
    And `logger` should be only required keyword argument.
    """

    def __init__(
        self,
        connection_manager: PostgresConnectionManager,
        **dependencies: DependencyInitializer,
    ):
        """Initialize middleware with connection pool and dependency factories."""
        super().__init__()
        self._connection_manager = connection_manager
        self._dependencies = dependencies
        self._lock = Lock()

    async def refresh(self):
        """Refresh database connection pool."""
        async with self._lock:
            await self._connection_manager.refresh()

    async def shutdown(self):
        """Shutdown database connection pool."""
        async with self._lock:
            await self._connection_manager.shutdown()

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Attach service dependencies to request state and process request."""
        request = get_http_request()
        for dependency, init in self._dependencies.items():
            setattr(request.state, dependency, init(self._connection_manager, logger=logger_dep.from_request(request)))
        return await call_next(context)

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, ResourceResult],
    ) -> ResourceResult:
        """Attach service dependencies to request state and process request."""
        request = get_http_request()
        for dependency, init in self._dependencies.items():
            setattr(request.state, dependency, init(self._connection_manager, logger=logger_dep.from_request(request)))
        return await call_next(context)
