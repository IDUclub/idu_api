"""FastAPI application initialization is performed here."""

import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import NoReturn

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
from idu_api.urban_api.middlewares.exception_handler import ExceptionHandlerMiddleware, HandlerNotFoundError
from idu_api.urban_api.middlewares.observability import ObservabilityMiddleware
from idu_api.urban_api.observability.logging import configure_logging
from idu_api.urban_api.observability.metrics import setup_metrics
from idu_api.urban_api.observability.otel_agent import OpenTelemetryAgent
from idu_api.urban_api.observability.utils import URLsMapper
from idu_api.urban_api.utils.auth_client import AuthenticationClient

from .handlers import list_of_routers
from .logic.impl.buffers import BufferServiceImpl
from .version import LAST_UPDATE, VERSION

STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = STATIC_DIR / "templates"


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


def load_config() -> UrbanAPIConfig:
    """Loading config using CONFIG_PATH environment variable."""
    if "CONFIG_PATH" not in os.environ:
        raise ValueError("CONFIG_PATH environment variable is not set")

    return UrbanAPIConfig.from_file(os.getenv("CONFIG_PATH"))


def setup_oauth(application: FastAPI, config: UrbanAPIConfig) -> None:
    """Setup oauth 2.0 OpenAPI schema."""

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema

        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )

        auth = config.auth

        openapi_schema.setdefault("components", {})
        openapi_schema["components"]["securitySchemes"] = {
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": auth.authorization_url,
                        "tokenUrl": auth.token_url,
                        "scopes": {},
                    }
                },
            }
        }

        openapi_schema["security"] = [{"OAuth2": []}]

        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi


def get_app(prefix: str = "/api", config: UrbanAPIConfig | None = None) -> FastAPI:
    """Create application and all dependable objects."""
    app_config: UrbanAPIConfig = config or load_config()

    description_path = STATIC_DIR / "description.txt"
    description = description_path.read_text(encoding="utf-8").strip()

    application = FastAPI(
        title="Urban API",
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

    application.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    setup_oauth(application, app_config)

    @application.get(f"{prefix}/docs", include_in_schema=False)
    async def custom_docs(request: Request):
        templates = Jinja2Templates(directory=TEMPLATES_DIR)
        description_html = description.replace("\n\n", "</p><p>").replace("\n", "<br>")
        description_html = f"<p>{description_html}</p>"
        return templates.TemplateResponse(
            "swagger_custom.html",
            {
                "request": request,
                "API_TITLE": application.title,
                "API_VERSION": application.version,
                "PREFIX": prefix,
                "TERMS_URL": application.terms_of_service,
                "CONTACT_EMAIL": application.contact["email"],
                "LICENSE_NAME": application.license_info.get("name", ""),
                "LICENSE_URL": application.license_info.get("url", ""),
                "OPENAPI_URL": application.openapi_url,
                "API_DESCRIPTION_HTML": description_html,
                "SWAGGER_CLIENT_ID": app_config.auth.client_id,
            },
        )

    @application.get("/api/oauth2-redirect.html", include_in_schema=False)
    async def oauth2_redirect():
        return FileResponse(STATIC_DIR / "oauth2-redirect.html")

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
    urls_mapper = URLsMapper()
    urls_mapper.add_routes(application.routes)

    auth_client = AuthenticationClient(config=app_config.auth)

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
        ExceptionHandlerMiddleware,
        debug=app_config.app.debug,
        exception_mapper=exception_mapper,
        urls_mapper=urls_mapper,
        errors_metric=metrics.http.errors,
    )
    application.add_middleware(
        ObservabilityMiddleware,
        metrics=metrics,
        urls_mapper=urls_mapper,
    )

    return application


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Lifespan function.

    Initializes database connection in pass_services_dependencies middleware.
    """
    app_config: UrbanAPIConfig = application.state.config
    logger = logger_dep.from_app(application)

    config_to_log = app_config.to_order_dict()
    await logger.ainfo("application is starting", config=config_to_log)

    kafka_producer_settings = KafkaProducerSettings.from_custom_config(app_config.broker)
    kafka_producer = KafkaProducerClient(
        kafka_producer_settings, logger=structlog.getLogger("broker")
    )  # requires event_loop
    kafka_producer_dep.init_dispencer(application, kafka_producer)

    await kafka_producer.start()

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

    for middleware in application.user_middleware:
        if middleware.cls == PassServicesDependenciesMiddleware:
            connection_manager: PostgresConnectionManager = middleware.kwargs["connection_manager"]
            await connection_manager.shutdown()

    otel_agent.shutdown()

    await kafka_producer.close()


app = get_app()
