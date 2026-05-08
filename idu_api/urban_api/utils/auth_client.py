"""FastAPI authentication client with Keycloak JWT verification."""

import asyncio
from typing import Any

import aiohttp
from aiohttp import ClientConnectorError
from cachetools import TTLCache
from jose import JWTError, jwt
from opentelemetry import trace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from idu_api.urban_api.config import AuthConfig
from idu_api.urban_api.dto.users import UserDTO
from idu_api.urban_api.exceptions.services.auth import (
    AuthTokenExpiredError,
    InvalidTokenSignature,
    JWTDecodeError,
)
from idu_api.urban_api.observability.utils import get_tracing_headers

_tracer = trace.get_tracer(__name__)


class AuthenticationClient:
    """Authentication client for validating jwt tokens and extract users from payload."""

    RETRIES = 3

    def __init__(self, config: AuthConfig):
        self.config = config

        self._jwks_cache = TTLCache(maxsize=1, ttl=config.jwks_cache_ttl)
        self._user_cache = TTLCache(
            maxsize=config.user_cache_size,
            ttl=config.user_cache_ttl,
        )

        self._lock = asyncio.Lock()

    # ------------------------
    # CONFIG UPDATE
    # ------------------------

    def update(self, config: AuthConfig) -> None:
        """Hot-reload configuration."""
        self.config = config

        self._jwks_cache = TTLCache(maxsize=1, ttl=config.jwks_cache_ttl)
        self._user_cache = TTLCache(
            maxsize=config.user_cache_size,
            ttl=config.user_cache_ttl,
        )

    # ------------------------
    # JWKS FETCHING
    # ------------------------

    @retry(
        stop=stop_after_attempt(RETRIES),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(ClientConnectorError),
    )
    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS (public keys) from Keycloak."""
        with _tracer.start_span("auth.fetch_jwks"):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.jwks_url,
                    headers=get_tracing_headers(),
                    timeout=self.config.timeout,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()

    async def get_jwks(self) -> dict[str, Any]:
        """Get JWKS with caching and concurrency protection."""
        if "jwks" in self._jwks_cache:
            return self._jwks_cache["jwks"]

        async with self._lock:
            if "jwks" in self._jwks_cache:
                return self._jwks_cache["jwks"]

            jwks = await self._fetch_jwks()
            self._jwks_cache["jwks"] = jwks
            return jwks

    # ------------------------
    # JWT PROCESSING
    # ------------------------

    async def _verify_jwt(self, token: str) -> dict[str, Any]:
        """Full JWT verification (signature + claims)."""
        try:  # pylint: disable=too-many-try-statements
            jwks = await self.get_jwks()

            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise InvalidTokenSignature()

            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if not key:
                raise InvalidTokenSignature()

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.config.server_url,
                options={"verify_aud": False},
            )

            if self.config.verify_aud:
                audiences = payload.get("aud", [])
                if isinstance(audiences, str):
                    audiences = [audiences]
                elif audiences is None:
                    audiences = []
                if not any(aud in self.config.valid_audiences for aud in audiences):
                    raise ValueError("Invalid audience")

            return payload

        except JWTError as exc:
            if "expired" in str(exc).lower():
                raise AuthTokenExpiredError() from exc
            raise InvalidTokenSignature() from exc
        except Exception as exc:
            raise JWTDecodeError() from exc

    async def process_token(self, token: str) -> dict[str, Any]:
        """Process token depending on verify flag."""
        if self.config.verify:
            return await self._verify_jwt(token)
        try:
            return jwt.get_unverified_claims(token)
        except Exception as exc:
            raise JWTDecodeError() from exc

    # ------------------------
    # ROLES EXTRACTION
    # ------------------------

    @staticmethod
    def extract_roles(payload: dict[str, Any]) -> list[str]:
        """Extract roles from Keycloak token."""
        roles: list[str] = []

        # realm roles
        roles.extend(payload.get("realm_access", {}).get("roles", []))

        # client roles
        resource_access = payload.get("resource_access", {})
        client_roles = resource_access.get("urban-api", {}).get("roles", [])
        roles.extend(client_roles)

        return roles

    # ------------------------
    # MAIN METHOD
    # ------------------------

    async def get_user_from_token(self, token: str) -> UserDTO:
        """Validate token and return UserDTO."""

        cached_user = self._user_cache.get(token)
        if cached_user:
            return cached_user

        payload = await self.process_token(token)

        roles = self.extract_roles(payload)

        user = UserDTO(
            id=payload.get("sub"),
            username=payload.get("preferred_username"),
            roles=roles,
            is_superuser="ADMIN" in roles,
            azp=payload.get("azp"),
        )

        self._user_cache[token] = user

        return user
