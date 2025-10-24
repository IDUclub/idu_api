# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""buffer type description

Revision ID: 5d671378237b
Revises: 19367879fde9
Create Date: 2025-10-24 18:03:52.408036

"""
from textwrap import dedent
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d671378237b"
down_revision: Union[str, None] = "19367879fde9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add new column `buffer_types_dict.description`
    op.add_column("buffer_types_dict", sa.Column("description", sa.String(4096), nullable=True))

    # fix buffer insert/update trigger (also for specified geometry)
    for schema in ("public", "user_projects"):
        if schema == "public":
            buffer_type_logic = f"""
                SELECT
                    CASE
                        WHEN uod.service_id IS NULL THEN pod.physical_object_type_id
                        ELSE NULL
                    END,
                    CASE
                        WHEN uod.service_id IS NOT NULL THEN sd.service_type_id
                        ELSE NULL
                    END
                INTO v_physical_object_type_id, v_service_type_id
                FROM {schema}.urban_objects_data uod
                LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                WHERE uod.urban_object_id = NEW.urban_object_id;
            """

            buffer_assignment_1 = f"""
                BEGIN
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    {buffer_type_logic}

                    SELECT buffer_value
                    INTO buffer_radius
                    FROM public.default_buffer_values_dict
                    WHERE buffer_type_id = NEW.buffer_type_id
                      AND (
                          (v_physical_object_type_id IS NOT NULL AND v_physical_object_type_id = default_buffer_values_dict.physical_object_type_id AND default_buffer_values_dict.service_type_id IS NULL)
                       OR (v_service_type_id IS NOT NULL AND v_service_type_id = default_buffer_values_dict.service_type_id AND default_buffer_values_dict.physical_object_type_id IS NULL)
                      )
                    LIMIT 1;

                    IF buffer_radius IS NULL THEN
                        RAISE EXCEPTION 'No standard buffer radius found for buffer_type_id=%, physical_object_type_id=%, service_type_id=%',
                            NEW.buffer_type_id, v_physical_object_type_id, v_service_type_id;
                    END IF;

                    BEGIN
                        NEW.geometry := ST_Difference(
                            ST_Transform(
                                ST_Buffer(v_object_geom::geography, buffer_radius)::geometry,
                                ST_SRID(v_object_geom)
                            ),
                            v_object_geom
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE NOTICE 'Buffer generation failed for urban_object_id=%', NEW.urban_object_id;
                        RETURN NEW;
                    END;
                END;
            """

            buffer_assignment_2 = f"""
                BEGIN
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;
                    
                    NEW.geometry := ST_MakeValid(NEW.geometry);
                    NEW.geometry := ST_Difference(NEW.geometry, v_object_geom);
                    IF NEW.geometry IS NULL OR ST_IsEmpty(NEW.geometry) THEN
                        RAISE NOTICE 'Resulting provided-buffer geometry is empty for urban_object_id=%', NEW.urban_object_id;
                    END IF;
                EXCEPTION WHEN OTHERS THEN
                    RAISE NOTICE 'Post-processing of provided geometry failed for urban_object_id=%', NEW.urban_object_id;
                    RETURN NEW;
                END;
            """
        else:
            buffer_type_logic = f"""
                SELECT
                    CASE
                        WHEN uod.service_id IS NULL AND uod.public_service_id IS NULL THEN
                            CASE
                                WHEN uod.physical_object_id IS NOT NULL THEN pod.physical_object_type_id
                                ELSE p_pod.physical_object_type_id
                            END
                        ELSE NULL
                    END,
                    CASE
                        WHEN uod.service_id IS NOT NULL THEN sd.service_type_id
                        WHEN uod.public_service_id IS NOT NULL THEN p_sd.service_type_id
                        ELSE NULL
                    END
                INTO v_physical_object_type_id, v_service_type_id
                FROM {schema}.urban_objects_data uod
                LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                LEFT JOIN public.physical_objects_data p_pod ON uod.public_physical_object_id = p_pod.physical_object_id
                LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                LEFT JOIN public.services_data p_sd ON uod.public_service_id = p_sd.service_id
                WHERE uod.urban_object_id = NEW.urban_object_id;
            """

            buffer_assignment_1 = f"""
                BEGIN
                    -- Get object geometry
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    {buffer_type_logic}

                    SELECT buffer_value
                    INTO buffer_radius
                    FROM public.default_buffer_values_dict
                    WHERE buffer_type_id = NEW.buffer_type_id
                      AND (
                          (v_physical_object_type_id IS NOT NULL AND v_physical_object_type_id = default_buffer_values_dict.physical_object_type_id AND default_buffer_values_dict.service_type_id IS NULL)
                       OR (v_service_type_id IS NOT NULL AND v_service_type_id = default_buffer_values_dict.service_type_id AND default_buffer_values_dict.physical_object_type_id IS NULL)
                      )
                    LIMIT 1;

                    IF buffer_radius IS NULL THEN
                        RAISE EXCEPTION 'No standard buffer radius found for buffer_type_id=%, physical_object_type_id=%, service_type_id=%',
                            NEW.buffer_type_id, v_physical_object_type_id, v_service_type_id;
                    END IF;

                    -- Get project's territory geometry
                    SELECT ptd.geometry, p.is_regional
                    INTO v_project_geom, v_is_regional
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.scenarios_data s ON uod.scenario_id = s.scenario_id
                    JOIN {schema}.projects_data p ON s.project_id = p.project_id
                    JOIN {schema}.projects_territory_data ptd ON p.project_id = ptd.project_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_project_geom IS NULL AND NOT v_is_regional THEN
                        RAISE EXCEPTION 'Could not find project territory geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    BEGIN

                        IF NOT v_is_regional THEN 
                            result_geom := ST_Intersection(
                                ST_Difference(
                                    ST_Transform(
                                        ST_Buffer(v_object_geom::geography, v_buffer_value)::geometry,
                                        ST_SRID(v_object_geom)
                                    ),
                                    v_object_geom
                                ),
                                v_project_geom
                            );
                        ELSE
                            result_geom := ST_Difference(
                                ST_Transform(
                                    ST_Buffer(v_object_geom::geography, v_buffer_value)::geometry,
                                    ST_SRID(v_object_geom)
                                ),
                                v_object_geom
                            );
                        END IF;

                        NEW.geometry := result_geom;

                    EXCEPTION WHEN OTHERS THEN
                        RAISE NOTICE 'Buffer generation failed for urban_object_id=%', NEW.urban_object_id;
                        RETURN NEW;
                    END;
                END;
            """

            buffer_assignment_2 = f"""
                BEGIN
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    NEW.geometry := ST_MakeValid(NEW.geometry);
                    NEW.geometry := ST_Difference(NEW.geometry, v_object_geom);
                    
                    IF (v_project_geom IS NOT NULL) AND (v_is_regional IS NOT TRUE) THEN
                        NEW.geometry := ST_Intersection(NEW.geometry, v_project_geom);
                    END IF;
                    
                    IF NEW.geometry IS NULL OR ST_IsEmpty(NEW.geometry) THEN
                        RAISE NOTICE 'Resulting provided-buffer geometry is empty for urban_object_id=%', NEW.urban_object_id;
                    END IF;
                EXCEPTION WHEN OTHERS THEN
                    RAISE NOTICE 'Post-processing of provided geometry failed for urban_object_id=%', NEW.urban_object_id;
                    RETURN NEW;
                END;
            """

        op.execute(
            sa.text(
                dedent(
                    f"""
                    CREATE OR REPLACE FUNCTION {schema}.trigger_set_default_buffer_geometry()
                    RETURNS trigger
                    LANGUAGE plpgsql
                    AS $function$
                    DECLARE
                        v_object_geom geometry;
                        buffer_radius FLOAT;
                        v_physical_object_type_id INT;
                        v_service_type_id INT;
                        v_project_geom GEOMETRY;
                        v_is_regional BOOLEAN;
                        result_geom GEOMETRY;
                    BEGIN
                        IF NEW.geometry IS NULL THEN
                            {buffer_assignment_1}
                        ELSE
                            {buffer_assignment_2}
                        END IF;

                        RETURN NEW;
                    END;
                    $function$;
                    """
                )
            )
        )


def downgrade() -> None:
    # add new column `buffer_types_dict.description`
    op.drop_column("buffer_types_dict", "description")

    # fix buffer insert/update trigger (also for specified geometry)
    for schema in ("public", "user_projects"):
        if schema == "public":
            buffer_type_logic = f"""
                SELECT
                    CASE
                        WHEN uod.service_id IS NULL THEN pod.physical_object_type_id
                        ELSE NULL
                    END,
                    CASE
                        WHEN uod.service_id IS NOT NULL THEN sd.service_type_id
                        ELSE NULL
                    END
                INTO v_physical_object_type_id, v_service_type_id
                FROM {schema}.urban_objects_data uod
                LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                WHERE uod.urban_object_id = NEW.urban_object_id;
            """

            buffer_assignment_1 = f"""
                BEGIN
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    {buffer_type_logic}

                    SELECT buffer_value
                    INTO buffer_radius
                    FROM public.default_buffer_values_dict
                    WHERE buffer_type_id = NEW.buffer_type_id
                      AND (
                          (v_physical_object_type_id IS NOT NULL AND v_physical_object_type_id = default_buffer_values_dict.physical_object_type_id AND default_buffer_values_dict.service_type_id IS NULL)
                       OR (v_service_type_id IS NOT NULL AND v_service_type_id = default_buffer_values_dict.service_type_id AND default_buffer_values_dict.physical_object_type_id IS NULL)
                      )
                    LIMIT 1;

                    IF buffer_radius IS NULL THEN
                        RAISE EXCEPTION 'No standard buffer radius found for buffer_type_id=%, physical_object_type_id=%, service_type_id=%',
                            NEW.buffer_type_id, v_physical_object_type_id, v_service_type_id;
                    END IF;

                    BEGIN
                        NEW.geometry := ST_Difference(
                            ST_Transform(
                                ST_Buffer(v_object_geom::geography, buffer_radius)::geometry,
                                ST_SRID(v_object_geom)
                            ),
                            v_object_geom
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE NOTICE 'Buffer generation failed for urban_object_id=%', NEW.urban_object_id;
                        RETURN NEW;
                    END;
                END;
            """
        else:
            buffer_type_logic = f"""
                SELECT
                    CASE
                        WHEN uod.service_id IS NULL AND uod.public_service_id IS NULL THEN
                            CASE
                                WHEN uod.physical_object_id IS NOT NULL THEN pod.physical_object_type_id
                                ELSE p_pod.physical_object_type_id
                            END
                        ELSE NULL
                    END,
                    CASE
                        WHEN uod.service_id IS NOT NULL THEN sd.service_type_id
                        WHEN uod.public_service_id IS NOT NULL THEN p_sd.service_type_id
                        ELSE NULL
                    END
                INTO v_physical_object_type_id, v_service_type_id
                FROM {schema}.urban_objects_data uod
                LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                LEFT JOIN public.physical_objects_data p_pod ON uod.public_physical_object_id = p_pod.physical_object_id
                LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                LEFT JOIN public.services_data p_sd ON uod.public_service_id = p_sd.service_id
                WHERE uod.urban_object_id = NEW.urban_object_id;
            """

            buffer_assignment_1 = f"""
                BEGIN
                    -- Get object geometry
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    {buffer_type_logic}

                    SELECT buffer_value
                    INTO buffer_radius
                    FROM public.default_buffer_values_dict
                    WHERE buffer_type_id = NEW.buffer_type_id
                      AND (
                          (v_physical_object_type_id IS NOT NULL AND v_physical_object_type_id = default_buffer_values_dict.physical_object_type_id AND default_buffer_values_dict.service_type_id IS NULL)
                       OR (v_service_type_id IS NOT NULL AND v_service_type_id = default_buffer_values_dict.service_type_id AND default_buffer_values_dict.physical_object_type_id IS NULL)
                      )
                    LIMIT 1;

                    IF buffer_radius IS NULL THEN
                        RAISE EXCEPTION 'No standard buffer radius found for buffer_type_id=%, physical_object_type_id=%, service_type_id=%',
                            NEW.buffer_type_id, v_physical_object_type_id, v_service_type_id;
                    END IF;

                    -- Get project's territory geometry
                    SELECT ptd.geometry, p.is_regional
                    INTO v_project_geom, v_is_regional
                    FROM {schema}.urban_objects_data uod
                    JOIN {schema}.scenarios_data s ON uod.scenario_id = s.scenario_id
                    JOIN {schema}.projects_data p ON s.project_id = p.project_id
                    JOIN {schema}.projects_territory_data ptd ON p.project_id = ptd.project_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;

                    IF v_project_geom IS NULL AND NOT v_is_regional THEN
                        RAISE EXCEPTION 'Could not find project territory geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;

                    BEGIN

                        IF NOT v_is_regional THEN 
                            result_geom := ST_Intersection(
                                ST_Difference(
                                    ST_Transform(
                                        ST_Buffer(v_object_geom::geography, v_buffer_value)::geometry,
                                        ST_SRID(v_object_geom)
                                    ),
                                    v_object_geom
                                ),
                                v_project_geom
                            );
                        ELSE
                            result_geom := ST_Difference(
                                ST_Transform(
                                    ST_Buffer(v_object_geom::geography, v_buffer_value)::geometry,
                                    ST_SRID(v_object_geom)
                                ),
                                v_object_geom
                            );
                        END IF;

                        NEW.geometry := result_geom;

                    EXCEPTION WHEN OTHERS THEN
                        RAISE NOTICE 'Buffer generation failed for urban_object_id=%', NEW.urban_object_id;
                        RETURN NEW;
                    END;
                END;
            """

        op.execute(
            sa.text(
                dedent(
                    f"""
                    CREATE OR REPLACE FUNCTION {schema}.trigger_set_default_buffer_geometry()
                    RETURNS trigger
                    LANGUAGE plpgsql
                    AS $function$
                    DECLARE
                        v_object_geom geometry;
                        buffer_radius FLOAT;
                        v_physical_object_type_id INT;
                        v_service_type_id INT;
                        v_project_geom GEOMETRY;
                        v_is_regional BOOLEAN;
                        result_geom GEOMETRY;
                    BEGIN
                        IF NEW.geometry IS NULL THEN
                            {buffer_assignment_1}
                        END IF;

                        RETURN NEW;
                    END;
                    $function$;
                    """
                )
            )
        )
