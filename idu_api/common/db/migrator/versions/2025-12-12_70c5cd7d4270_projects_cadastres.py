# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""projects cadastres

Revision ID: 70c5cd7d4270
Revises: a7c0c662fa0c
Create Date: 2025-12-12 15:53:46.762630

"""
from textwrap import dedent
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "70c5cd7d4270"
down_revision: Union[str, None] = "a7c0c662fa0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("projects_cadastres_data_id_seq", schema="user_projects")))
    op.create_table(
        "projects_cadastres_data",
        sa.Column(
            "project_cadastre_id",
            sa.Integer(),
            server_default=sa.text("nextval('user_projects.projects_cadastres_data_id_seq')"),
            nullable=False,
        ),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry", nullable=False
            ),
            nullable=False,
        ),
        sa.Column(
            "centre_point",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry", nullable=False
            ),
            nullable=False,
        ),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("area", sa.Float(precision=53), nullable=True),
        sa.Column("cad_num", sa.String(), nullable=True),
        sa.Column("cost_value", sa.Float(precision=53), nullable=True),
        sa.Column("land_record_area", sa.Float(precision=53), nullable=True),
        sa.Column("land_record_category_type", sa.String(), nullable=True),
        sa.Column("ownership_type", sa.String(), nullable=True),
        sa.Column("permitted_use_established_by_document", sa.String(), nullable=True),
        sa.Column("quarter_cad_number", sa.String(), nullable=True),
        sa.Column("readable_address", sa.Text(), nullable=True),
        sa.Column("specified_area", sa.Float(precision=53), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("zone_pzz", sa.String(), nullable=True),
        sa.Column("possible_pzz_vri", sa.String(), nullable=True),
        sa.Column("possible_vri_list", sa.Text(), nullable=True),
        sa.Column("similarity_score", sa.Float(precision=53), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["user_projects.projects_data.project_id"],
            name=op.f("projects_cadastres_data_fk_projects_data"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_cadastre_id", name=op.f("projects_cadastres_data_pk")),
        schema="user_projects",
    )

    for trigger_name, table_name, procedure_name in [
        (
            "check_geometry_correctness_trigger",
            "user_projects.projects_cadastres_data",
            "public.trigger_validate_geometry",
        ),
        (
            "set_center_point_trigger_trigger",
            "user_projects.projects_cadastres_data",
            "public.trigger_set_centre_point",
        ),
    ]:
        op.execute(
            sa.text(
                dedent(
                    f"""
                    CREATE TRIGGER {trigger_name}
                    BEFORE INSERT OR UPDATE ON {table_name}
                    FOR EACH ROW
                    EXECUTE PROCEDURE {procedure_name}();
                    """
                )
            )
        )


def downgrade() -> None:
    op.drop_table("projects_cadastres_data", schema="user_projects")
    op.execute(sa.schema.DropSequence(sa.Sequence("projects_cadastres_data_id_seq", schema="user_projects")))
