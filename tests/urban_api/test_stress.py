import asyncio
import math
import statistics
import time

import click
import numpy as np
import structlog
from otteroad import KafkaProducerClient, KafkaProducerSettings
from shapely import transform

from idu_api.common.db.config import DBConfig
from idu_api.common.db.connection import PostgresConnectionManager
from idu_api.urban_api.config import UrbanAPIConfig
from idu_api.urban_api.dto import UserDTO
from idu_api.urban_api.logic.impl.helpers.physical_objects import get_physical_objects_around_from_db
from idu_api.urban_api.logic.impl.helpers.projects_objects import add_project_to_db
from idu_api.urban_api.minio.services.projects_storage import ProjectStorageManager
from idu_api.urban_api.schemas import ProjectTerritoryPost
from idu_api.urban_api.schemas.geometries import Geometry
from idu_api.urban_api.schemas.projects import ProjectPost

BUFFER_METERS = 5_000
EARTH_RADIUS_METERS = 6_371_008.8
MIN_OBJECTS_COUNT = 10_000
RUNS = 30


def test_geometry() -> Geometry:
    return Geometry(
        type="Polygon",
        coordinates=[
            [
                (30.22, 59.86),
                (30.22, 59.85),
                (30.25, 59.85),
                (30.25, 59.86),
                (30.22, 59.86),
            ]
        ],
    )


def buffer_wgs84_geometry_meters(geometry, buffer_meters: int):
    centroid = geometry.centroid
    lon0_rad = math.radians(centroid.x)
    lat0_rad = math.radians(centroid.y)
    cos_lat0 = math.cos(lat0_rad)

    def to_local_meters(coords: np.ndarray) -> np.ndarray:
        lon_rad = np.radians(coords[:, 0])
        lat_rad = np.radians(coords[:, 1])
        return np.column_stack(
            (
                (lon_rad - lon0_rad) * cos_lat0 * EARTH_RADIUS_METERS,
                (lat_rad - lat0_rad) * EARTH_RADIUS_METERS,
            )
        )

    def to_wgs84(local_coords: np.ndarray) -> np.ndarray:
        lon = np.degrees(local_coords[:, 0] / (EARTH_RADIUS_METERS * cos_lat0) + lon0_rad)
        lat = np.degrees(local_coords[:, 1] / EARTH_RADIUS_METERS + lat0_rad)
        return np.column_stack((lon, lat))

    return transform(transform(geometry, to_local_meters).buffer(buffer_meters), to_wgs84)


def project_10k_objects() -> ProjectPost:
    territory = ProjectTerritoryPost(geometry=test_geometry())

    return ProjectPost(
        name="Performance test project",
        description="Performance test project",
        territory_id=3138,
        public=False,
        is_regional=False,
        is_city=False,
        properties={},
        territory=territory,
    )


async def test_get_physical_objects_around_p95(connection_manager: PostgresConnectionManager):
    """
    Performance test for get_physical_objects_around_from_db.

    Requirement:
        p95 response time < 5000 ms
        for searching more than 10 000 objects in 5000 m buffer.
    """

    durations_ms: list[float] = []
    objects_counts: list[int] = []

    geometry = test_geometry().as_shapely_geometry()

    for run_idx in range(RUNS):
        started_at = time.perf_counter()

        async with connection_manager.get_connection() as conn:
            objects = await get_physical_objects_around_from_db(
                conn=conn,
                geometry=geometry,
                physical_object_type_id=None,
                buffer_meters=BUFFER_METERS,
            )

        duration_ms = (time.perf_counter() - started_at) * 1000
        objects_count = len(objects)

        durations_ms.append(duration_ms)
        objects_counts.append(objects_count)

        assert objects_count > MIN_OBJECTS_COUNT, (
            f"Expected more than {MIN_OBJECTS_COUNT} objects, " f"got {objects_count}"
        )

    durations_ms.sort()

    p95_index = math.ceil(0.95 * RUNS) - 1
    p95_ms = durations_ms[p95_index]

    avg_ms = statistics.mean(durations_ms)
    median_ms = statistics.median(durations_ms)
    max_ms = max(durations_ms)
    min_ms = min(durations_ms)

    min_objects = min(objects_counts)
    max_objects = max(objects_counts)

    print("\n=== get_physical_objects_around_from_db statistics ===")
    print(f"Runs count: {RUNS}")
    print(f"Buffer: {BUFFER_METERS} m")
    print(f"Objects count: {min_objects}..{max_objects}")
    print(f"Min:    {min_ms:.2f} ms")
    print(f"Max:    {max_ms:.2f} ms")
    print(f"Avg:    {avg_ms:.2f} ms")
    print(f"Median: {median_ms:.2f} ms")
    print(f"p95:    {p95_ms:.2f} ms")
    print("=====================================================\n")

    assert p95_ms < 10000, (
        f"get_physical_objects_around_from_db p95 is too slow: " f"{p95_ms:.2f} ms (expected < 10000 ms)"
    )


async def test_project_creation_p95(
    connection_manager: PostgresConnectionManager,
    project: ProjectPost,
    user: UserDTO,
    kafka_producer: KafkaProducerClient,
    project_storage_manager: ProjectStorageManager,
    logger: structlog.BoundLogger,
):
    """
    Performance test for project creation.

    Requirement:
        p95 project creation time < 5000 ms
        for projects containing up to 10 000 objects.
    """
    kafka_producer.init_loop()
    await kafka_producer.start()

    durations_ms: list[float] = []

    for run_idx in range(RUNS):
        started_at = time.perf_counter()

        async with connection_manager.get_connection() as conn:
            await add_project_to_db(
                conn=conn,
                project=project,
                user=user,
                kafka_producer=kafka_producer,
                project_storage_manager=project_storage_manager,
                logger=logger,
            )

        duration_ms = (time.perf_counter() - started_at) * 1000

        durations_ms.append(duration_ms)

    durations_ms.sort()

    p95_index = math.ceil(0.95 * RUNS) - 1
    p95_ms = durations_ms[p95_index]

    avg_ms = statistics.mean(durations_ms)
    median_ms = statistics.median(durations_ms)
    max_ms = max(durations_ms)
    min_ms = min(durations_ms)

    print("\n=== add_project_to_db statistics ===")
    print(f"Runs count: {RUNS}")
    print(f"Min:    {min_ms:.2f} ms")
    print(f"Max:    {max_ms:.2f} ms")
    print(f"Avg:    {avg_ms:.2f} ms")
    print(f"Median: {median_ms:.2f} ms")
    print(f"p95:    {p95_ms:.2f} ms")
    print("==============================\n")

    assert p95_ms < 10000, f"Project creation p95 is too slow: " f"{p95_ms:.2f} ms (expected < 10000 ms)"


async def async_main(
    connection_manager: PostgresConnectionManager,
    project: ProjectPost,
    user: UserDTO,
    kafka_producer: KafkaProducerClient,
    project_storage_manager: ProjectStorageManager,
    logger: structlog.BoundLogger,
):
    await test_get_physical_objects_around_p95(connection_manager)

    await test_project_creation_p95(
        connection_manager=connection_manager,
        project=project,
        user=user,
        kafka_producer=kafka_producer,
        project_storage_manager=project_storage_manager,
        logger=logger,
    )


# ------------------------
# CLI
# ------------------------


@click.command("stress-test")
@click.option("--config_path", envvar="CONFIG_PATH", required=True)
def main(config_path: str):
    """Run a stress-test script."""
    config = UrbanAPIConfig.load(config_path)

    project = project_10k_objects()

    user = UserDTO(id="user_id", username="test user", is_superuser=True, roles=["ADMIN"], azp="test")

    kafka_settings = KafkaProducerSettings.from_custom_config(config.broker)
    kafka_producer = KafkaProducerClient(producer_settings=kafka_settings, init_loop=False)

    project_storage_manager = ProjectStorageManager(app_config=config)

    logger = structlog.getLogger("stress-test")

    connection_manager = PostgresConnectionManager(
        master=DBConfig(
            host=config.db.master.host,
            port=config.db.master.port,
            database=config.db.master.database,
            user=config.db.master.user,
            password=config.db.master.password,
            pool_size=1,
            debug=config.app.debug,
        ),
        replicas=config.db.replicas or [],
        logger=logger,
        application_name="duty_stress_test",
    )

    asyncio.run(async_main(connection_manager, project, user, kafka_producer, project_storage_manager, logger))


if __name__ == "__main__":
    main()
