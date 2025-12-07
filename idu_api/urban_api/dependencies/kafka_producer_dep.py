"""Kafka producer dependency for FastAPI applications is defined here.

This module provides a dependency function for injecting an initialized
`KafkaProducerClient` instance from the FastAPI application state. It is
intended to be used with FastAPI's dependency injection system in route
handlers and background tasks.

Example usage:

    from fastapi import Depends

    @app.post("/events/")
    async def publish_event(
        event: MyEventModel,
        producer: KafkaProducerClient = Depends(obtain),
    ):
        await producer.send(event)

The producer instance should be initialized during FastAPI startup and attached
to `app.state.kafka_producer`.
"""

from fastapi import FastAPI, Request
from otteroad import KafkaProducerClient


def init_dispencer(app: FastAPI, kafka_producer: KafkaProducerClient) -> None:
    """Initialize KafkaProducer dispencer at app's state."""
    if hasattr(app.state, "kafka_producer_dep"):
        if not isinstance(app.state.kafka_producer_dep, KafkaProducerClient):
            raise ValueError(
                "kafka_producer_dep attribute of app's state is already"
                f" set with other value ({app.state.kafka_producer_dep})"
            )
        return

    app.state.kafka_producer_dep = kafka_producer


def from_app(app: FastAPI) -> KafkaProducerClient:
    """Get a KafkaProducer from request's app state."""
    if not hasattr(app.state, "kafka_producer_dep"):
        raise ValueError("KafkaProducer dispencer was not initialized at app preparation")
    return app.state.kafka_producer_dep


def from_request(request: Request) -> KafkaProducerClient:
    """Get a KafkaProducer from request's app state."""
    return from_app(request.app)
