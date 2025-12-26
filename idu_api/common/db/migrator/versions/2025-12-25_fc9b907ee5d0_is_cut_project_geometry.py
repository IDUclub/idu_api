# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""is_cut project geometry

Revision ID: fc9b907ee5d0
Revises: 70c5cd7d4270
Create Date: 2025-12-25 13:28:29.162492

"""
from textwrap import dedent
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fc9b907ee5d0"
down_revision: Union[str, None] = "70c5cd7d4270"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "object_geometries_data",
        sa.Column("is_cut", sa.Boolean(), nullable=False, server_default="false"),
        schema="user_projects",
    )

    op.execute(
        sa.text(
            dedent(
                """
                UPDATE user_projects.object_geometries_data pog
                SET is_cut = TRUE
                WHERE pog.public_object_geometry_id IS NOT NULL
                  AND EXISTS (
                    SELECT 1
                    FROM user_projects.urban_objects_data uo
                    JOIN user_projects.scenarios_data s ON uo.scenario_id = s.scenario_id
                    JOIN user_projects.projects_territory_data pt ON s.project_id = pt.project_id
                    JOIN public.object_geometries_data public_geom ON public_geom.object_geometry_id = pog.public_object_geometry_id
                    WHERE pog.object_geometry_id = uo.object_geometry_id
                      AND NOT ST_Contains(pt.geometry, public_geom.geometry)  -- НЕ полностью входит
                      AND ST_Intersects(pt.geometry, public_geom.geometry)    -- пересекается
                  );
                """
            )
        )
    )


def downgrade() -> None:
    op.drop_column("object_geometries_data", "is_cut", schema="user_projects")
