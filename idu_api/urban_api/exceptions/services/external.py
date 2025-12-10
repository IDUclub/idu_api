"""Exceptions connected with external services are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class ExternalServiceResponseError(UrbanApiError):
    """Exception to raise when external service returns http error."""

    def __init__(self, service: str, error: str, status_code: int):
        self.service = service
        self.error = error
        self.status_code = status_code


class ExternalServiceUnavailable(UrbanApiError):
    """Exception to raise when external service is unavailable."""

    def __init__(self, service: str):
        self.service = service
