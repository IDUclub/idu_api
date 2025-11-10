# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""tech schema indicator binds

Revision ID: 6a88033136f5
Revises: 5d671378237b
Create Date: 2025-11-07 14:29:12.787488

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a88033136f5"
down_revision: Union[str, None] = "5d671378237b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema("tech"))

    op.create_table(
        "territory_indicators_binds_data",
        sa.Column("indicator_id", sa.Integer(), nullable=False),
        sa.Column("territory_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("min_value", sa.Float(precision=53), nullable=False),
        sa.Column("max_value", sa.Float(precision=53), nullable=False),
        sa.ForeignKeyConstraint(
            ["indicator_id"],
            ["indicators_dict.indicator_id"],
            name=op.f("territory_indicators_binds_data_fk_indicator_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["territory_id"],
            ["territories_data.territory_id"],
            name=op.f("territory_indicators_binds_data_fk_territory_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "indicator_id", "territory_id", "level", name=op.f("pk_territory_indicators_binds_data")
        ),
        schema="tech",
    )


def downgrade() -> None:
    op.execute(sa.schema.DropSchema("tech", cascade=True))
