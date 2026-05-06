"""FastMCP application initialization is performed here."""

import os
from collections.abc import Callable

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan
from fastmcp.server.lifespan import lifespan as mcp_lifespan
from mcp import McpError
from sqlalchemy.exc import DBAPIError, IntegrityError

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
from idu_api.urban_api.utils.auth_client import AuthenticationClient
from idu_api.urban_mcp.dependencies import auth_dep, logger_dep, metrics_dep
from idu_api.urban_mcp.exceptions import UrbanMCPError
from idu_api.urban_mcp.exceptions.logic.mapper import register_exceptions as register_logic_errors
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper
from idu_api.urban_mcp.exceptions.services.mapper import register_exceptions as register_services_errors
from idu_api.urban_mcp.handlers import list_of_routers
from idu_api.urban_mcp.middlewares.dependency_injection import PassServicesDependenciesMiddleware
from idu_api.urban_mcp.middlewares.exception_handler import ExceptionHandlerMiddleware
from idu_api.urban_mcp.middlewares.observability import ObservabilityMiddleware
from idu_api.urban_mcp.observability.metrics import setup_metrics
from idu_api.urban_mcp.observability.otel_agent import OpenTelemetryAgent

from .config import UrbanMCPConfig
from .observability.logging import configure_logging
from .version import LAST_UPDATE, VERSION


def load_config() -> UrbanMCPConfig:
    """Loading config using MCP_CONFIG_PATH environment variable."""
    if "MCP_CONFIG_PATH" not in os.environ:
        raise ValueError("MCP_CONFIG_PATH environment variable is not set")

    return UrbanMCPConfig.from_file(os.getenv("MCP_CONFIG_PATH"))


def bind_routers(mcp: FastMCP) -> None:
    """Mount MCP routers."""
    for router in list_of_routers:
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


def get_app(path: str = "/mcp", config: UrbanMCPConfig | None = None) -> StarletteWithLifespan:
    """Create application and all dependable objects."""
    app_config: UrbanMCPConfig = config or load_config()
    logger = configure_logging(
        app_config.observability.logging,
        tracing_enabled=app_config.observability.jaeger is not None,
    )

    mcp = FastMCP(
        name="Urban MCP",
        version=f"{VERSION} ({LAST_UPDATE})",
        lifespan=create_lifespan(app_config, logger),
    )
    bind_routers(mcp)

    connection_manager = PostgresConnectionManager(
        master=app_config.db.master,
        replicas=app_config.db.replicas,
        logger=logger,
        application_name=f"urban_mcp_{VERSION}",
    )

    metrics = setup_metrics()
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

    auth_client = AuthenticationClient(config=app_config.auth)

    application = mcp.http_app(path=path)
    application.state.config = app_config

    auth_dep.init_dispencer(application, auth_client)
    logger_dep.init_dispencer(application, logger)
    metrics_dep.init_dispencer(application, metrics)

    return application


def create_lifespan(app_config, logger):
    @mcp_lifespan
    async def lifespan(server: FastMCP):
        config_to_log = app_config.to_order_dict()

        await logger.ainfo(
            "application is starting",
            config=config_to_log,
        )

        otel_agent = OpenTelemetryAgent(
            app_config.observability.prometheus,
            app_config.observability.jaeger,
        )

        if not app_config.auth.verify:
            await logger.awarning(
                "JWT verification is DISABLED. Tokens are not validated and may be forged. "
                "This mode must NOT be used in production."
            )

        yield

        for middleware in server.middleware:
            if isinstance(middleware, PassServicesDependenciesMiddleware):
                await middleware.shutdown()

        otel_agent.shutdown()

    return lifespan


app = get_app()
