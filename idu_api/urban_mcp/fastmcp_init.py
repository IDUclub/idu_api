"""FastMCP application initialization is performed here."""

import os
from collections.abc import Callable, Iterable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan
from mcp import McpError
from otteroad import KafkaProducerClient, KafkaProducerSettings
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.applications import Starlette
from starlette.routing import Mount

from idu_api.common.db.connection.manager import PostgresConnectionManager
from idu_api.urban_api.exceptions.utils.translate import translate_db_constraint_error
from idu_api.urban_api.logic.impl.buffers import BufferServiceImpl
from idu_api.urban_api.logic.impl.functional_zones import FunctionalZonesServiceImpl
from idu_api.urban_api.logic.impl.indicators import IndicatorsServiceImpl
from idu_api.urban_api.logic.impl.object_geometries import ObjectGeometriesServiceImpl
from idu_api.urban_api.logic.impl.physical_object_types import PhysicalObjectTypesServiceImpl
from idu_api.urban_api.logic.impl.physical_objects import PhysicalObjectsServiceImpl
from idu_api.urban_api.logic.impl.projects import UserProjectServiceImpl
from idu_api.urban_api.logic.impl.service_types import ServiceTypesServiceImpl
from idu_api.urban_api.logic.impl.services import ServicesDataServiceImpl
from idu_api.urban_api.logic.impl.soc_groups import SocGroupsServiceImpl
from idu_api.urban_api.logic.impl.system import SystemServiceImpl
from idu_api.urban_api.logic.impl.territories import TerritoriesServiceImpl
from idu_api.urban_api.logic.impl.urban_objects import UrbanObjectsServiceImpl
from idu_api.urban_api.minio.services.projects_storage import get_project_storage_manager_from_config
from idu_api.urban_api.utils.auth_client import AuthenticationClient
from idu_api.urban_mcp.dependencies import (
    auth_dep,
    kafka_producer_dep,
    logger_dep,
    metrics_dep,
    project_storage_dep,
)
from idu_api.urban_mcp.exceptions import UrbanMCPError
from idu_api.urban_mcp.exceptions.logic.mapper import register_exceptions as register_logic_errors
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper
from idu_api.urban_mcp.exceptions.services.mapper import register_exceptions as register_services_errors
from idu_api.urban_mcp.groups import MCP_GROUPS, MCPGroup
from idu_api.urban_mcp.middlewares.dependency_injection import PassServicesDependenciesMiddleware
from idu_api.urban_mcp.middlewares.exception_handler import ExceptionHandlerMiddleware
from idu_api.urban_mcp.middlewares.observability import ObservabilityMiddleware
from idu_api.urban_mcp.observability.metrics import Metrics, setup_metrics
from idu_api.urban_mcp.observability.otel_agent import OpenTelemetryAgent

from .config import UrbanMCPConfig
from .observability.logging import configure_logging
from .version import LAST_UPDATE, VERSION


@dataclass
class MCPMountedApp:
    """Created FastMCP server and its Starlette HTTP application."""

    group: MCPGroup
    mcp: FastMCP
    app: StarletteWithLifespan


@dataclass
class MCPRuntime:
    """Shared runtime objects for all mounted MCP group applications."""

    config: UrbanMCPConfig
    logger: structlog.BoundLogger
    metrics: Metrics
    kafka_producer: KafkaProducerClient
    otel_agent: OpenTelemetryAgent | None = None
    mounted_apps: list[MCPMountedApp] = field(default_factory=list)


def load_config() -> UrbanMCPConfig:
    """Load config using MCP_CONFIG_PATH environment variable."""

    if "MCP_CONFIG_PATH" not in os.environ:
        raise ValueError("MCP_CONFIG_PATH environment variable is not set")

    return UrbanMCPConfig.from_file(os.getenv("MCP_CONFIG_PATH"))


def bind_routers(mcp: FastMCP, routers: Iterable[FastMCP]) -> None:
    """Mount only selected MCP routers."""

    for router in routers:
        mcp.mount(router)


def register_exceptions(mapper: ExceptionMapper) -> None:
    """Register application and database exception mappings to MCP errors."""

    mapper.register_simple(UrbanMCPError, -32603, "Unexpected error happened in Urban MCP")

    register_logic_errors(mapper)
    register_services_errors(mapper)

    def translate_if_possible(mapper: ExceptionMapper, exc: Exception) -> McpError:
        """Translate DB constraint errors recursively before applying mapping."""

        exc_after_map = translate_db_constraint_error(exc)
        if exc_after_map != exc:
            return translate_if_possible(mapper, exc_after_map)
        return mapper.apply(exc)

    mapper.register_func(IntegrityError, lambda exc: translate_if_possible(mapper, exc))
    mapper.register_func(DBAPIError, lambda exc: translate_if_possible(mapper, exc))


def create_kafka_producer(app_config: UrbanMCPConfig) -> KafkaProducerClient | None:
    """Create Kafka producer if broker config is provided."""

    if app_config.broker is None:
        return None

    kafka_producer_settings = KafkaProducerSettings.from_custom_config(app_config.broker)

    return KafkaProducerClient(
        kafka_producer_settings,
        logger=structlog.getLogger("broker"),
        init_loop=False,
    )


def setup_middlewares(
    *,
    mcp: FastMCP,
    app_config: UrbanMCPConfig,
    logger: structlog.BoundLogger,
    metrics: Metrics,
) -> None:
    """Register common MCP middlewares."""

    connection_manager = PostgresConnectionManager(
        master=app_config.db.master,
        replicas=app_config.db.replicas,
        logger=logger,
        application_name=f"urban_mcp_{VERSION}",
    )

    exception_mapper = ExceptionMapper()
    register_exceptions(exception_mapper)

    def ignore_kwargs(func: Callable) -> Callable:
        def wrapped(*args, **_kwargs):
            return func(*args)

        return wrapped

    mcp.add_middleware(ObservabilityMiddleware(metrics=metrics))
    mcp.add_middleware(
        ExceptionHandlerMiddleware(
            debug=app_config.app.debug,
            exception_mapper=exception_mapper,
            errors_metric=metrics.mcp.errors,
        )
    )
    mcp.add_middleware(
        PassServicesDependenciesMiddleware(
            connection_manager=connection_manager,
            buffers_service=ignore_kwargs(BufferServiceImpl),
            functional_zones_service=ignore_kwargs(FunctionalZonesServiceImpl),
            indicators_service=ignore_kwargs(IndicatorsServiceImpl),
            object_geometries_service=ignore_kwargs(ObjectGeometriesServiceImpl),
            physical_object_types_service=ignore_kwargs(PhysicalObjectTypesServiceImpl),
            physical_objects_service=ignore_kwargs(PhysicalObjectsServiceImpl),
            service_types_service=ignore_kwargs(ServiceTypesServiceImpl),
            services_data_service=ignore_kwargs(ServicesDataServiceImpl),
            soc_groups_service=ignore_kwargs(SocGroupsServiceImpl),
            territories_service=ignore_kwargs(TerritoriesServiceImpl),
            urban_objects_service=ignore_kwargs(UrbanObjectsServiceImpl),
            user_project_service=UserProjectServiceImpl,
            system_service=SystemServiceImpl,
        ),
    )


def init_application_dependencies(
    *,
    application: StarletteWithLifespan,
    runtime: MCPRuntime,
) -> None:
    """Initialize dependency dispensers for MCP handlers."""

    auth_client = AuthenticationClient(config=runtime.config.auth)

    application.state.config = runtime.config

    auth_dep.init_dispencer(application, auth_client)
    logger_dep.init_dispencer(application, runtime.logger)
    metrics_dep.init_dispencer(application, runtime.metrics)
    project_storage_dep.init_dispencer(application, get_project_storage_manager_from_config(runtime.config))
    kafka_producer_dep.init_dispencer(application, runtime.kafka_producer)


def create_mcp_group_app(
    *,
    group: MCPGroup,
    runtime: MCPRuntime,
) -> MCPMountedApp:
    """Create Starlette application for one MCP tool group.

    Each group gets its own FastMCP instance. Therefore, tools/list returns
    only tools mounted into this specific group.

    Heavy application resources are managed by root_lifespan, not by FastMCP
    group lifespans.
    """

    mcp = FastMCP(
        name=f"Urban MCP: {group.name}",
        instructions=group.description,
        version=f"{VERSION} ({LAST_UPDATE})",
    )

    bind_routers(mcp, [group.router])

    setup_middlewares(
        mcp=mcp,
        app_config=runtime.config,
        logger=runtime.logger,
        metrics=runtime.metrics,
    )

    # Internal MCP path is "/"; an external path is provided by Starlette Mount.
    application = mcp.http_app(path="/")

    application.state.config = runtime.config
    application.state.mcp_group = group.name
    application.state.mcp_group_description = group.description

    init_application_dependencies(
        application=application,
        runtime=runtime,
    )

    return MCPMountedApp(
        group=group,
        mcp=mcp,
        app=application,
    )


async def shutdown_mcp_middlewares(runtime: MCPRuntime) -> None:
    """Shutdown dependency injection middlewares for all MCP servers."""

    for mounted_app in runtime.mounted_apps:
        for middleware in mounted_app.mcp.middleware:
            if isinstance(middleware, PassServicesDependenciesMiddleware):
                await middleware.shutdown()


@asynccontextmanager
async def root_lifespan(app: Starlette):
    """Run shared startup and shutdown logic once for the root application.

    This lifespan starts and stops common infrastructure once:
    Kafka producer, OpenTelemetry agent and shared middleware resources.

    It also enters FastMCP HTTP application lifespans so that FastMCP
    Streamable HTTP session managers are initialized correctly for each
    mounted MCP endpoint.
    """

    runtime: MCPRuntime = app.state.runtime
    config_to_log = runtime.config.to_order_dict()

    await runtime.logger.ainfo(
        "application is starting",
        config=config_to_log,
    )

    runtime.otel_agent = OpenTelemetryAgent(
        runtime.config.observability.prometheus,
        runtime.config.observability.jaeger,
    )

    runtime.kafka_producer.init_loop()
    await runtime.kafka_producer.start()

    if not runtime.config.auth.verify:
        await runtime.logger.awarning(
            "JWT verification is DISABLED. Tokens are not validated and may be forged. "
            "This mode must NOT be used in production."
        )

    async with AsyncExitStack() as stack:
        for mounted_app in runtime.mounted_apps:
            lifespan_context = get_lifespan_context(mounted_app.app)
            if lifespan_context is not None:
                await stack.enter_async_context(lifespan_context(mounted_app.app))

        try:
            yield
        finally:
            await shutdown_mcp_middlewares(runtime)

            runtime.otel_agent.shutdown()

            await runtime.kafka_producer.close()


def get_lifespan_context(application: StarletteWithLifespan) -> Callable[[Any], Any] | None:
    """Return Starlette/FastMCP lifespan context from an application.

    FastMCP http_app returns StarletteWithLifespan. Depending on the concrete
    Starlette/FastMCP version, lifespan can be available either on the app
    itself or on the router.
    """

    lifespan_context = getattr(application, "lifespan", None)
    if lifespan_context is not None:
        return lifespan_context

    router = getattr(application, "router", None)
    if router is not None:
        return getattr(router, "lifespan_context", None)

    return None


def get_app(config: UrbanMCPConfig | None = None) -> Starlette:
    """Create root Starlette application with several mounted MCP endpoints."""

    app_config: UrbanMCPConfig = config or load_config()

    logger = configure_logging(
        app_config.observability.logging,
        tracing_enabled=app_config.observability.jaeger is not None,
    )

    runtime = MCPRuntime(
        config=app_config,
        logger=logger,
        metrics=setup_metrics(),
        kafka_producer=create_kafka_producer(app_config),
    )

    routes = []

    for group in MCP_GROUPS:
        mounted_app = create_mcp_group_app(
            group=group,
            runtime=runtime,
        )

        runtime.mounted_apps.append(mounted_app)
        routes.append(Mount(group.path, app=mounted_app.app))

    app = Starlette(
        routes=routes,
        lifespan=root_lifespan,
    )

    app.state.runtime = runtime

    return app


app = get_app()
