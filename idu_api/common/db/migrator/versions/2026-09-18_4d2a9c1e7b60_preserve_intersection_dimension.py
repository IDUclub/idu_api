# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""preserve intersection dimension

Revision ID: 4d2a9c1e7b60
Revises: fc9b907ee5d0
Create Date: 2026-09-18 00:00:00.000000

"""
from textwrap import dedent
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d2a9c1e7b60"
down_revision: Union[str, None] = "fc9b907ee5d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.normalize_intersection(a geometry, b geometry)
                RETURNS geometry AS $$
                BEGIN
                    RETURN ST_CollectionExtract(
                        ST_Intersection(a, b),
                        ST_Dimension(a) + 1
                    );
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.normalize_intersection(a geometry, b geometry)
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
