# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""normalize geometry

Revision ID: a7c0c662fa0c
Revises: 89402c8953bb
Create Date: 2025-11-21 17:13:08.720141

"""
from textwrap import dedent
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c0c662fa0c"
down_revision: Union[str, None] = "89402c8953bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION normalize_intersection(a geometry, b geometry)
                RETURNS geometry AS $$
                DECLARE
                    geom geometry := ST_Intersection(a, b);
                BEGIN
                    IF ST_GeometryType(geom) = 'ST_GeometryCollection' THEN
                        RETURN ST_Multi(ST_CollectionExtract(geom, 3));
                    ELSE
                        RETURN geom;
                    END IF;
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """
            )
        )
    )


def downgrade() -> None:
    op.execute(sa.text("""DROP FUNCTION IF EXISTS normalize_intersection(geometry, geometry);"""))
