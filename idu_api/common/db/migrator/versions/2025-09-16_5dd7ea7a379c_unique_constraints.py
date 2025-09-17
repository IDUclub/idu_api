# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""unique constraints

Revision ID: 5dd7ea7a379c
Revises: cfd14b6653f8
Create Date: 2025-09-16 12:46:41.676518

"""
from textwrap import dedent
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5dd7ea7a379c"
down_revision: Union[str, None] = "49e0b7a9fea0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # fix unique constraint on `public.default_buffer_values_dict`
    op.drop_constraint("default_buffer_values_dict_unique", "default_buffer_values_dict")
    op.execute(
        sa.text(
            dedent(
                """
                CREATE UNIQUE INDEX default_buffer_values_dict_unique
                    ON default_buffer_values_dict (
                           buffer_type_id,
                           COALESCE(physical_object_type_id, -1),
                           COALESCE(service_type_id, -1)
                        )
                """
            )
        )
    )

    # fix unique constraint on `public.soc_group_values_data`
    op.drop_constraint("soc_values_data_unique_key", "soc_group_values_data")
    op.execute(
        sa.text(
            dedent(
                """
                CREATE UNIQUE INDEX soc_group_values_data_unique
                    ON soc_group_values_data (
                          soc_group_id,
                          service_type_id,
                          COALESCE(soc_value_id, -1)
                        )
                """
            )
        )
    )

    # fix unique constraint on `user_projects.indicators_data`
    op.drop_constraint("indicators_data_unique", "indicators_data", schema="user_projects")
    op.execute(
        sa.text(
            dedent(
                """
                CREATE UNIQUE INDEX indicators_data_unique
                    ON user_projects.indicators_data (
                          indicator_id,
                          scenario_id,
                          COALESCE(territory_id, -1),
                          COALESCE(hexagon_id, -1)
                        )
                """
            )
        )
    )

    # fix index on `buildings_data.physical_object_id`
    op.execute(  # drop duplicates
        sa.text(
            dedent(
                """
                WITH duplicates AS (
                    SELECT physical_object_id, min(building_id) AS keep_building_id, count(*) 
                    FROM buildings_data 
                    GROUP BY physical_object_id 
                    HAVING count(*) > 1
                ), to_delete AS (
                    SELECT building_id AS delete_building_id 
                    FROM buildings_data 
                    WHERE physical_object_id IN (SELECT physical_object_id FROM duplicates) 
                      AND building_id NOT IN (SELECT keep_building_id FROM duplicates)
                ) 
                DELETE FROM buildings_data WHERE building_id IN (SELECT delete_building_id FROM to_delete);
                """
            )
        )
    )
    op.drop_index("living_buildings_data_physical_object_id_idx", "buildings_data", if_exists=True)
    op.drop_index("buildings_data_physical_object_id_idx", "buildings_data", if_exists=True)
    op.create_index(
        "buildings_data_physical_object_id_idx",
        "buildings_data",
        ["physical_object_id"],
        unique=True,
    )
    op.execute(  # drop duplicates
        sa.text(
            dedent(
                """
                WITH duplicates AS (
                    SELECT physical_object_id, min(building_id) AS keep_building_id, count(*) 
                    FROM user_projects.buildings_data 
                    GROUP BY physical_object_id 
                    HAVING count(*) > 1
                ), to_delete AS (
                    SELECT building_id AS delete_building_id 
                    FROM user_projects.buildings_data 
                    WHERE physical_object_id IN (SELECT physical_object_id FROM duplicates) 
                      AND building_id NOT IN (SELECT keep_building_id FROM duplicates)
                ) 
                DELETE FROM user_projects.buildings_data WHERE building_id IN (SELECT delete_building_id FROM to_delete);
                """
            )
        )
    )
    op.drop_index("buildings_data_physical_object_id_idx", "buildings_data", schema="user_projects")
    op.create_index(
        "buildings_data_physical_object_id_idx",
        "buildings_data",
        ["physical_object_id"],
        unique=True,
        schema="user_projects",
    )


def downgrade() -> None:
    op.drop_index("default_buffer_values_dict_unique", "default_buffer_values_dict")
    op.create_unique_constraint(
        "default_buffer_values_dict_unique",
        "default_buffer_values_dict",
        ["buffer_type_id", "physical_object_type_id", "service_type_id"],
    )

    op.drop_index("soc_group_values_data_unique", "soc_group_values_data")
    op.create_unique_constraint(
        "soc_values_data_unique_key",
        "soc_group_values_data",
        ["soc_group_id", "service_type_id", "soc_value_id"],
    )

    op.drop_index("indicators_data_unique", "indicators_data", schema="user_projects")
    op.create_unique_constraint(
        "indicators_data_unique",
        "indicators_data",
        ["indicator_id", "scenario_id", "territory_id", "hexagon_id"],
        schema="user_projects",
    )

    op.drop_index("buildings_data_physical_object_id_idx", "buildings_data")
    op.create_index(
        "living_buildings_data_physical_object_id_idx",
        "buildings_data",
        ["physical_object_id"],
    )
    op.drop_index("buildings_data_physical_object_id_idx", "buildings_data", schema="user_projects")
    op.create_index(
        "buildings_data_physical_object_id_idx", "buildings_data", ["physical_object_id"], schema="user_projects"
    )
