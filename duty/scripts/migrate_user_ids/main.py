"""Duty script to migrate user_id from email to Keycloak sub."""

import asyncio

import aiohttp
import click
import structlog
from sqlalchemy import update, select

from idu_api.common.db.connection.manager import PostgresConnectionManager
from idu_api.common.db.entities import projects_data
from idu_api.urban_api.config import DBConfig, UrbanAPIConfig


# ------------------------
# KEYCLOAK CLIENT
# ------------------------

class KeycloakAdminClient:
    """Minimal Keycloak Admin REST client."""

    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret

        self._token: str | None = None

    async def get_token(self) -> str:
        """Get admin access token using client credentials."""
        url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self._token = data["access_token"]
                return self._token

    async def get_users(self) -> list[dict]:
        """Fetch all users (with pagination)."""
        if not self._token:
            await self.get_token()

        users: list[dict] = []
        first = 0
        page_size = 100

        async with aiohttp.ClientSession() as session:
            while True:
                url = f"{self.base_url}/admin/realms/{self.realm}/users"

                async with session.get(
                    url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    params={"first": first, "max": page_size},
                ) as resp:
                    resp.raise_for_status()
                    batch = await resp.json()

                if not batch:
                    break

                users.extend(batch)
                first += page_size

        return users


# ------------------------
# MIGRATION LOGIC
# ------------------------

def build_email_mapping(users: list[dict], logger) -> dict[str, str]:
    """Build email -> sub mapping."""
    mapping: dict[str, str] = {}

    for user in users:
        email = user.get("email")
        sub = user.get("id")

        if not email:
            logger.warning("user without email skipped", user_id=sub)
            continue

        if email in mapping:
            logger.warning("duplicate email detected", email=email)

        mapping[email] = sub

    logger.info("mapping built", total=len(mapping))
    return mapping


async def migrate_user_ids(
    connection_manager: PostgresConnectionManager,
    mapping: dict[str, str],
    logger,
):
    """Update user_id in projects_data."""
    async with connection_manager.get_connection() as conn:
        result = await conn.execute(select(projects_data.c.user_id))
        all_users = result.scalars().all()

        unique_emails = set(all_users)
        logger.info("found users in db", unique=len(unique_emails))

        updated = 0
        missing = 0

        for email in unique_emails:
            sub = mapping.get(email.lower())

            if not sub:
                logger.warning("no mapping for email", email=email)
                missing += 1
                continue

            stmt = (
                update(projects_data)
                .where(projects_data.c.user_id == email)
                .values(user_id=sub)
            )

            result = await conn.execute(stmt)
            updated += result.rowcount or 0

        await conn.commit()

        logger.info(
            "migration finished",
            updated_rows=updated,
            missing_emails=missing,
        )


# ------------------------
# MAIN
# ------------------------

async def async_main(
    connection_manager: PostgresConnectionManager,
    logger: structlog.stdlib.BoundLogger,
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
):
    """Main migration flow."""

    kc = KeycloakAdminClient(
        base_url=keycloak_url,
        realm=realm,
        client_id=client_id,
        client_secret=client_secret,
    )

    logger.info("fetching users from keycloak")

    users = await kc.get_users()

    logger.info("users fetched", count=len(users))

    mapping = build_email_mapping(users, logger)

    await migrate_user_ids(connection_manager, mapping, logger)


# ------------------------
# CLI
# ------------------------

@click.command("migrate-user-ids")
@click.option("--config_path", envvar="CONFIG_PATH", required=True)
@click.option("--keycloak_url", required=True, help="Keycloak base URL (e.g. http://localhost:8080)")
@click.option("--realm", required=True, help="Keycloak realm")
@click.option("--client_id", required=True)
@click.option("--client_secret", required=True)
def main(
    config_path: str,
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
):
    """Run migration script."""

    config = UrbanAPIConfig.load(config_path)

    logger = structlog.getLogger("migrate-user-ids")

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
        application_name="duty_migrate_user_ids",
    )

    asyncio.run(
        async_main(
            connection_manager,
            logger,
            keycloak_url,
            realm,
            client_id,
            client_secret,
        )
    )


if __name__ == "__main__":
    main()
