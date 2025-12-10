"""Exceptions connected with authentication client are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class AuthTokenExpiredError(UrbanApiError):
    """Exception to raise when token has expired."""


class JWTDecodeError(UrbanApiError):
    """Exception to raise when token decoding has failed."""


class InvalidTokenSignature(UrbanApiError):
    """Exception to raise when validating token by external service has failed."""
