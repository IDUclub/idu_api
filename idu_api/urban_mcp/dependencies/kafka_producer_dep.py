"""KafkaProducerClient dependency functions are defined here."""

from fastmcp.server.http import StarletteWithLifespan
from otteroad import KafkaProducerClient
from starlette.requests import Request


def init_dispencer(app: StarletteWithLifespan, kafka_producer: KafkaProducerClient) -> None:
    """Initialize KafkaProducer dispencer at app's state."""
    if hasattr(app.state, "kafka_producer_dep"):
        if not isinstance(app.state.kafka_producer_dep, KafkaProducerClient):
            raise ValueError(
                "kafka_producer_dep attribute of app's state is already"
                f" set with other value ({app.state.kafka_producer_dep})"
            )
        return

    app.state.kafka_producer_dep = kafka_producer


def from_app(app: StarletteWithLifespan) -> KafkaProducerClient:
    """Get a KafkaProducer from app state."""
    if not hasattr(app.state, "kafka_producer_dep"):
        raise ValueError("KafkaProducer dispencer was not initialized at app preparation")
    return app.state.kafka_producer_dep


async def from_request(request: Request) -> KafkaProducerClient:
    """Get a KafkaProducer from request's app state."""
    return from_app(request.app)
