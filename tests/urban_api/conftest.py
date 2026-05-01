"""Full integration test setup with testcontainers."""

import time
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.sql.expression import text
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.network import Network
from testcontainers.kafka import KafkaContainer
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer

from idu_api.common.db.config import DBConfig, MultipleDBsConfig
from idu_api.common.utils.secrets import SecretStr
from idu_api.urban_api.config import (
    AppConfig,
    AuthConfig,
    BrokerConfig,
    CORSConfig,
    FileServerConfig,
    UrbanAPIConfig,
    UvicornConfig,
)
from idu_api.urban_api.fastapi_init import get_app
from idu_api.urban_api.observability.config import LoggingConfig, ObservabilityConfig

from .helpers import *

# ---------------------------------------------------------------------------
# Postgres (PostGIS)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres():
    context_path = Path(__file__).resolve().parent.parent.parent / "urban_api"
    image = DockerImage(path=context_path, dockerfile_path="postgis.Dockerfile", tag="postgis-ru:test")
    image.build()

    with PostgresContainer("postgis-ru:test") as pg:
        yield pg


def run_migrations(dsn: str):
    alembic_dir = Path(__file__).resolve().parent.parent.parent / "idu_api" / "common" / "db"

    alembic_cfg = Config(str(alembic_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(alembic_dir / "migrator"))
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)

    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db(request, config: UrbanAPIConfig):
    """
    Clean all tables in the database before each test.

    Uses TRUNCATE ... CASCADE to remove all data while preserving schema.
    This ensures test isolation without re-running migrations.
    """
    if "integration" not in request.node.nodeid:
        return

    db = config.db.master

    dsn = f"postgresql+asyncpg://{db.user}:{db.password.get_secret_value()}" f"@{db.host}:{db.port}/{db.database}"

    engine = create_async_engine(dsn)

    schemas = ["public", "user_projects", "tech"]

    async with engine.begin() as conn:
        await conn.execute(text("SET session_replication_role = 'replica';"))

        result = await conn.execute(
            text(
                """
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname = ANY(:schemas)
                """
            ),
            {"schemas": schemas},
        )

        tables = result.fetchall()

        if tables:
            full_table_names = [f"{schema}.{table}" for schema, table in tables if "sys" not in table]

            truncate_query = "TRUNCATE TABLE " + ", ".join(full_table_names) + " RESTART IDENTITY CASCADE;"
            await conn.execute(text(truncate_query))

        await conn.execute(text("SET session_replication_role = 'origin';"))

    await engine.dispose()


# ---------------------------------------------------------------------------
# MinIO
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def minio():
    with MinioContainer("minio/minio:RELEASE.2025-02-07T23-21-09Z") as mc:
        host = mc.get_container_host_ip()
        port = mc.get_exposed_port(9000)

        endpoint = f"http://{host}:{port}"

        client = mc.get_client()

        bucket = "projects.images"

        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        yield {
            "endpoint": endpoint,
            "access_key": mc.access_key,
            "secret_key": mc.secret_key,
            "bucket": bucket,
        }


# ---------------------------------------------------------------------------
# Kafka + Schema Registry
# ---------------------------------------------------------------------------


TOPICS = ["urban.events", "scenario.events", "indicator.events"]


def wait_for_kafka(bootstrap_servers: str, timeout: int = 20):
    """Wait until Kafka is ready to accept admin connections."""
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    start = time.time()
    while time.time() - start < timeout:
        try:
            admin.list_topics(timeout=2)
            return
        except Exception:
            time.sleep(1)

    raise RuntimeError("Kafka did not become ready in time")


def create_topics(bootstrap_servers: str, topics: list[str]):
    """Create Kafka topics if they do not exist."""
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    existing_topics = admin.list_topics(timeout=5).topics.keys()

    new_topics = [
        NewTopic(topic, num_partitions=1, replication_factor=1) for topic in topics if topic not in existing_topics
    ]

    if new_topics:
        futures = admin.create_topics(new_topics)

        for topic, future in futures.items():
            try:
                future.result()
            except Exception as e:
                raise RuntimeError(f"Failed to create topic {topic}: {e}")


@pytest.fixture(scope="session")
def kafka():
    with Network() as network:
        # --- Kafka ---
        kafka = KafkaContainer("confluentinc/cp-kafka:7.9.6")
        kafka.with_network(network)
        kafka.with_network_aliases("kafka")
        kafka.start()

        bootstrap_servers = kafka.get_bootstrap_server()

        # --- WAIT FOR KAFKA ---
        wait_for_kafka(bootstrap_servers)

        # --- CREATE TOPICS ---
        create_topics(bootstrap_servers, TOPICS)

        # --- Schema Registry ---
        schema_registry = DockerContainer("confluentinc/cp-schema-registry:7.9.6")
        schema_registry.with_network(network)
        schema_registry.with_env(
            "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS",
            "PLAINTEXT://kafka:9092",
        )
        schema_registry.with_env("SCHEMA_REGISTRY_HOST_NAME", "schema-registry")
        schema_registry.with_env("SCHEMA_REGISTRY_LISTENERS", "http://0.0.0.0:8081")
        schema_registry.with_exposed_ports(8081)
        schema_registry.start()

        schema_registry_url = (
            f"http://{schema_registry.get_container_host_ip()}:{schema_registry.get_exposed_port(8081)}"
        )

        yield {
            "bootstrap": bootstrap_servers,
            "schema_registry": schema_registry_url,
        }

        schema_registry.stop()
        kafka.stop()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def config(postgres, minio, kafka) -> UrbanAPIConfig:
    # ---------------- DB ----------------
    host = postgres.get_container_host_ip()
    port = int(postgres.get_exposed_port(5432))

    db = MultipleDBsConfig(
        master=DBConfig(
            host=host,
            port=port,
            user=postgres.username,
            password=SecretStr(postgres.password),
            database=postgres.dbname,
            pool_size=1,
        ),
    )

    dsn = f"postgresql+asyncpg://{postgres.username}:{postgres.password}@{host}:{port}/{postgres.dbname}"
    run_migrations(dsn)

    # ---------------- MinIO ----------------
    fileserver = FileServerConfig(
        url=minio["endpoint"],
        access_key=minio["access_key"],
        secret_key=minio["secret_key"],
        projects_bucket=minio["bucket"],
    )

    # ---------------- Kafka ----------------
    broker = BrokerConfig(
        client_id="urban-api",
        bootstrap_servers=kafka["bootstrap"],
        schema_registry_url=kafka["schema_registry"],
        enable_idempotence=True,
    )

    # ---------------- Keycloak ----------------
    auth = AuthConfig(verify=False)

    # ------------- Observability --------------

    observability = ObservabilityConfig(logging=LoggingConfig())

    # ---------------- misc ----------------
    app = AppConfig(
        uvicorn=UvicornConfig(host="0.0.0.0", port=8000, reload=False, forwarded_allow_ips=["127.0.0.1"]),
        debug=False,
        cors=CORSConfig(["*"], ["*"], ["*"], True),
    )

    cfg = UrbanAPIConfig(
        app=app,
        db=db,
        auth=auth,
        fileserver=fileserver,
        broker=broker,
        observability=observability,
    )

    return cfg


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def app(config):
    return get_app(config=config)


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def client(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
