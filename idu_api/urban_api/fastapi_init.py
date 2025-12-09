"""FastAPI application initialization is performed here."""

import os
from contextlib import asynccontextmanager
from typing import Callable, NoReturn

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi_pagination import add_pagination
from otteroad import KafkaProducerClient, KafkaProducerSettings

from idu_api.common.db.connection.manager import PostgresConnectionManager
from idu_api.common.exceptions.mapper import ExceptionMapper
from idu_api.urban_api.config import UrbanAPIConfig
from idu_api.urban_api.dependencies import auth_dep, kafka_producer_dep, logger_dep, metrics_dep
from idu_api.urban_api.exceptions.mapper import register_exceptions
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
from idu_api.urban_api.middlewares.dependency_injection import PassServicesDependenciesMiddleware
from idu_api.urban_api.middlewares.exception_handler import ExceptionHandlerMiddleware
from idu_api.urban_api.middlewares.observability import HandlerNotFoundError, ObservabilityMiddleware
from idu_api.urban_api.observability.metrics import setup_metrics
from idu_api.urban_api.observability.otel_agent import OpenTelemetryAgent
from idu_api.urban_api.utils.auth_client import AuthenticationClient
from idu_api.urban_api.utils.observability import URLsMapper, configure_logging

from .handlers import list_of_routers
from .logic.impl.buffers import BufferServiceImpl
from .version import LAST_UPDATE, VERSION


def bind_routes(application: FastAPI, prefix: str, debug: bool) -> None:
    """Bind all routes to application."""
    for router in list_of_routers:
        if not debug:
            to_remove = []
            for i, route in enumerate(router.routes):
                if "debug" in route.path:
                    to_remove.append(i)
            for i in to_remove[::-1]:
                del router.routes[i]
        if len(router.routes) > 0:
            application.include_router(router, prefix=(prefix if "/" not in {r.path for r in router.routes} else ""))


def get_app(prefix: str = "/api") -> FastAPI:
    """Create application and all dependable objects."""

    if "CONFIG_PATH" not in os.environ:
        raise ValueError("CONFIG_PATH environment variable is not set")
    app_config: UrbanAPIConfig = UrbanAPIConfig.from_file(os.getenv("CONFIG_PATH"))

    description = "This is a Digital Territories Platform API to access and manipulate basic territories data."

    application = FastAPI(
        title="Digital Territories Platform Data API",
        description=description,
        docs_url=None,
        openapi_url=f"{prefix}/openapi",
        version=f"{VERSION} ({LAST_UPDATE})",
        terms_of_service="http://swagger.io/terms/",
        contact={"email": "idu@itmo.ru"},
        license_info={"name": "Apache 2.0", "url": "http://www.apache.org/licenses/LICENSE-2.0.html"},
        lifespan=lifespan,
    )
    bind_routes(application, prefix, app_config.app.debug)

    @application.get(f"{prefix}/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui.css",
        )

    @application.exception_handler(404)
    async def handle_404(request: Request, exc: Exception) -> NoReturn:
        raise HandlerNotFoundError() from exc

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.app.cors.allow_origins,
        allow_credentials=app_config.app.cors.allow_credentials,
        allow_methods=app_config.app.cors.allow_methods,
        allow_headers=app_config.app.cors.allow_headers,
    )
    application.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

    add_pagination(application)

    def ignore_kwargs(func: Callable) -> Callable:
        def wrapped(*args, **_kwargs):
            return func(*args)

        return wrapped

    application.state.config = app_config

    logger = configure_logging(
        app_config.observability.logging,
        tracing_enabled=app_config.observability.jaeger is not None,
    )
    metrics = setup_metrics()
    exception_mapper = ExceptionMapper()
    register_exceptions(exception_mapper)
    connection_manager = PostgresConnectionManager(
        master=app_config.db.master,
        replicas=app_config.db.replicas,
        logger=logger,
        application_name=f"urban_api_{VERSION}",
    )
    urls_mapper = URLsMapper(app_config.observability.prometheus.urls_mapping)
    auth_client = AuthenticationClient(
        app_config.auth.cache_size,
        app_config.auth.cache_ttl,
        app_config.auth.validate,
        app_config.auth.url,
    )

    metrics_dep.init_dispencer(application, metrics)
    logger_dep.init_dispencer(application, logger)
    auth_dep.init_dispencer(application, auth_client)

    application.add_middleware(
        PassServicesDependenciesMiddleware,
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
    )
    application.add_middleware(
        ObservabilityMiddleware,
        exception_mapper=exception_mapper,
        metrics=metrics,
        urls_mapper=urls_mapper,
    )
    application.add_middleware(
        ExceptionHandlerMiddleware,
        debug=app_config.app.debug,
        exception_mapper=exception_mapper,
    )

    return application


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Lifespan function.

    Initializes database connection in pass_services_dependencies middleware.
    """
    app_config: UrbanAPIConfig = application.state.config
    logger = logger_dep.from_app(application)

    await logger.ainfo("application is starting", config=app_config.to_order_dict())

    kafka_producer_settings = KafkaProducerSettings.from_custom_config(app_config.broker)
    kafka_producer = KafkaProducerClient(
        kafka_producer_settings, logger=structlog.getLogger("broker")
    )  # required event_loop
    kafka_producer_dep.init_dispencer(application, kafka_producer)

    await kafka_producer.start()

    otel_agent = OpenTelemetryAgent(
        app_config.observability.prometheus,
        app_config.observability.jaeger,
    )

    yield

    for middleware in application.user_middleware:
        if middleware.cls == PassServicesDependenciesMiddleware:
            connection_manager: PostgresConnectionManager = middleware.kwargs["connection_manager"]
            await connection_manager.shutdown()

    otel_agent.shutdown()

    await kafka_producer.close()


app = get_app()
