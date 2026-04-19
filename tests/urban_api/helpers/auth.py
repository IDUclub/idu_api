"""All fixtures for authentication tests are defined here."""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from jose import jwt

__all__ = ["expired_token", "superuser_token", "valid_token"]


# ------------------------
# TEST KEY (RSA, как в Keycloak)
# ------------------------

PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxG0v7cZp1v2mQ0g6m6gqQ6m6m6m6m6m6m6m6m6m6m6m6m6
6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m6m
-----END RSA PRIVATE KEY-----
"""

ISSUER = "https://keycloak.test/realms/TEST"
AUDIENCE = "urban-api"


# ------------------------
# FIXTURES
# ------------------------


@pytest.fixture(scope="session")
def superuser_token() -> str:
    """Valid superuser JWT token."""
    return create_token(
        sub="admin",
        roles=["ADMIN", "USER"],
        is_superuser=True,
        expired=False,
    )


@pytest.fixture(scope="session")
def valid_token() -> str:
    """Valid user JWT token."""
    return create_token(
        sub="user1",
        roles=["USER"],
        is_superuser=False,
        expired=False,
    )


@pytest.fixture(scope="session")
def expired_token() -> str:
    """Expired JWT token."""
    return create_token(
        sub="user1",
        roles=["USER"],
        is_superuser=False,
        expired=True,
    )


# ------------------------
# TOKEN CREATION
# ------------------------


def create_token(
    sub: str,
    roles: list[str],
    is_superuser: bool,
    expired: bool,
) -> str:
    """Create RS256 JWT compatible with Keycloak-like structure."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": sub,
        "preferred_username": sub,
        "email": f"{sub}@test.local",
        "exp": int((now - timedelta(hours=1)).timestamp()) if expired else int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": ISSUER,
        "aud": [AUDIENCE],
        "azp": "test-client",
        "realm_access": {"roles": roles},
        "resource_access": {"urban-api": {"roles": roles}},
        "is_superuser": is_superuser,
    }

    token = jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    return token
