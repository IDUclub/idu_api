# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""project phase properties

Revision ID: 49e0b7a9fea0
Revises: 01ceb2ef5830
Create Date: 2025-08-19 11:20:33.980396

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "49e0b7a9fea0"
down_revision: Union[str, None] = "01ceb2ef5830"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add column `properties` to `user_projects.projects_phases_data` table
    op.add_column(
        "projects_phases_data",
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="user_projects",
    )


def downgrade() -> None:
    # drop new column
    op.drop_column("projects_phases_data", "properties", schema="user_projects")
