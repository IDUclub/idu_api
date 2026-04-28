"""Tests for temporary infrastructure are defined here."""

import time

import boto3
import pytest
import requests
from confluent_kafka import Consumer, Producer
from httpx import AsyncClient


def wait_for_http(url: str, timeout: int = 20):
    start = time.time()

    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code < 500:
                return r
        except requests.RequestException:
            pass

        time.sleep(1)

    return None


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_ping(client: AsyncClient):
    """
    Verify that the application is up and responds to basic health check.

    This is a smoke test ensuring:
    - FastAPI app started correctly
    - routing is configured
    - ASGI lifespan completed successfully
    """
    response = await client.get("/health_check/ping")

    assert response.status_code == 200
    assert response.json() is not None


@pytest.mark.asyncio
async def test_health_db(client: AsyncClient):
    """
    Verify that the database is reachable through API layer.

    This test ensures:
    - DB connection manager is initialized
    - application can execute SQL queries
    - DB container is accessible
    """
    response = await client.get("/health_check/db")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# MinIO (S3)
# ---------------------------------------------------------------------------


def test_minio_bucket_exists(config):
    """
    Verify that MinIO is running and required bucket exists.

    This ensures:
    - MinIO container is accessible
    - credentials are correct
    - bucket initialization logic worked
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=config.fileserver.url,
        aws_access_key_id=config.fileserver.access_key,
        aws_secret_access_key=config.fileserver.secret_key.get_secret_value(),
        region_name=config.fileserver.region_name,
    )

    buckets = s3.list_buckets()
    bucket_names = [b["Name"] for b in buckets["Buckets"]]

    assert config.fileserver.projects_bucket in bucket_names


# ---------------------------------------------------------------------------
# Kafka
# ---------------------------------------------------------------------------


def test_kafka_produce_consume(config):
    """
    Verify that Kafka broker is working by producing and consuming a message.

    This ensures:
    - Kafka container is reachable
    - producer can send messages
    - consumer can receive messages
    """
    topic = "test-topic"

    producer = Producer(
        {
            "bootstrap.servers": config.broker.bootstrap_servers,
        }
    )

    consumer = Consumer(
        {
            "bootstrap.servers": config.broker.bootstrap_servers,
            "group.id": "test-group",
            "auto.offset.reset": "earliest",
        }
    )

    consumer.subscribe([topic])

    # produce message
    producer.produce(topic, b"hello-test")
    producer.flush()

    # wait & poll
    msg = None
    timeout = time.time() + 10

    while time.time() < timeout:
        msg = consumer.poll(1.0)
        if msg is not None and not msg.error():
            break

    consumer.close()

    assert msg is not None, "No message received from Kafka"
    assert msg.value() == b"hello-test"


# ---------------------------------------------------------------------------
# Schema Registry
# ---------------------------------------------------------------------------


def test_schema_registry_available(config):
    """
    Verify that Schema Registry is up and responding.

    This ensures:
    - Schema Registry container is reachable
    - HTTP API is available
    """
    url = f"{config.broker.schema_registry_url}/subjects"

    response = wait_for_http(url)

    assert response is not None
    assert response.status_code == 200
