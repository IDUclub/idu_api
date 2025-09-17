# pylint: disable=no-member,invalid-name,missing-function-docstring,too-many-statements
"""add err codes for triggers

Revision ID: 19367879fde9
Revises: 5dd7ea7a379c
Create Date: 2025-09-17 17:18:44.216665

"""
from textwrap import dedent
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19367879fde9"
down_revision: Union[str, None] = "5dd7ea7a379c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # geometry triggers
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_validate_geometry()
                 RETURNS trigger
                 LANGUAGE plpgsql
                AS $function$
                BEGIN
                    IF TG_OP = 'UPDATE' AND OLD.geometry = NEW.geometry THEN
                        return NEW;
                    END IF;
                    IF NOT (ST_GeometryType(NEW.geometry) 
                    IN ('ST_Point', 'ST_Polygon', 'ST_MultiPolygon', 'ST_LineString', 'ST_MultiLineString')) THEN
                        RAISE EXCEPTION 'Передан неверный тип геометрии!' USING ERRCODE = 'P0101';
                    END IF;
                
                    IF ST_IsEmpty(NEW.geometry) THEN
                        RAISE EXCEPTION 'Передана пустая геометрия!'  USING ERRCODE = 'P0102';
                    END IF;

                    IF NOT ST_IsValid(NEW.geometry) THEN
                        RAISE EXCEPTION 'Передана некорректная геометрия!' USING ERRCODE = 'P0103';
                    END IF;
                
                    RETURN NEW;
                END;
                $function$
                ;
                """
            )
        )
    )

    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_validate_geometry_not_point()
                 RETURNS trigger
                 LANGUAGE plpgsql
                AS $function$
                BEGIN
                    IF TG_OP = 'UPDATE' AND OLD.geometry = NEW.geometry THEN
                        return NEW;
                    END IF;
                    IF NOT (ST_GeometryType(NEW.geometry) IN ('ST_Polygon', 'ST_MultiPolygon')) THEN
                        RAISE EXCEPTION 'Передан неверный тип геометрии!' USING ERRCODE = 'P0101';
                    END IF;
                
                    IF ST_IsEmpty(NEW.geometry) THEN
                        RAISE EXCEPTION 'Передана пустая геометрия!' USING ERRCODE = 'P0102';
                    END IF;

                    IF NOT ST_IsValid(NEW.geometry) THEN
                        RAISE EXCEPTION 'Передана некорректная геометрия: %', ST_AsText(NEW.geometry) USING ERRCODE = 'P0103';
                    END IF;
                
                    RETURN NEW;
                END;
                $function$
                ;
                """
            )
        )
    )

    # buffer triggers
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_set_default_buffer_geometry()
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
                
                    BEGIN
                        SELECT ogd.geometry
                        INTO v_object_geom
                        FROM public.urban_objects_data uod
                        JOIN public.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                        WHERE uod.urban_object_id = NEW.urban_object_id;
                    
                        IF v_object_geom IS NULL THEN
                            RAISE EXCEPTION 'Не удалось найти геометрию для urban_object_id=%', NEW.urban_object_id 
                                USING ERRCODE = 'P0111';
                        END IF;
                    
                    
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
                    FROM public.urban_objects_data uod
                    LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                    LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;
                    
                    
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
                            RAISE EXCEPTION 'Не удалось найти дефолтный радиус буфера для buffer_type_id=%, physical_object_type_id=%, service_type_id=%',
                                NEW.buffer_type_id, v_physical_object_type_id, v_service_type_id
                                USING ERRCODE = 'P0112';
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
                            RAISE NOTICE 'Не удалось создать буфер urban_object_id=%', NEW.urban_object_id;
                            RETURN NEW;
                        END;
                    END;
                    END IF;
                    RETURN NEW;
                END;
                $function$
                ;
                """
            )
        )
    )


def downgrade() -> None:
    # geometry triggers
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_validate_geometry()
                 RETURNS trigger
                 LANGUAGE plpgsql
                AS $function$
                BEGIN
                    IF TG_OP = 'UPDATE' AND OLD.geometry = NEW.geometry THEN
                        return NEW;
                    END IF;
                    IF NOT (ST_GeometryType(NEW.geometry) 
                    IN ('ST_Point', 'ST_Polygon', 'ST_MultiPolygon', 'ST_LineString', 'ST_MultiLineString')) THEN
                        RAISE EXCEPTION 'Invalid geometry type!';
                    END IF;
                
                    IF NOT ST_IsValid(NEW.geometry) THEN
                        RAISE EXCEPTION 'Invalid geometry!';
                    END IF;
                
                    IF ST_IsEmpty(NEW.geometry) THEN
                        RAISE EXCEPTION 'Empty geometry!';
                    END IF;
                
                    RETURN NEW;
                END;
                $function$
                ;
                """
            )
        )
    )

    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_validate_geometry_not_point()
                 RETURNS trigger
                 LANGUAGE plpgsql
                AS $function$
                BEGIN
                    IF TG_OP = 'UPDATE' AND OLD.geometry = NEW.geometry THEN
                        return NEW;
                    END IF;
                    IF NOT (ST_GeometryType(NEW.geometry) IN ('ST_Polygon', 'ST_MultiPolygon')) THEN
                        RAISE EXCEPTION 'Invalid geometry type!';
                    END IF;
                
                    IF NOT ST_IsValid(NEW.geometry) THEN
                        RAISE EXCEPTION 'Invalid geometry!';
                    END IF;
                
                    IF ST_IsEmpty(NEW.geometry) THEN
                        RAISE EXCEPTION 'Empty geometry!';
                    END IF;
                
                    RETURN NEW;
                END;
                $function$
                ;
                """
            )
        )
    )

    # buffer triggers
    op.execute(
        sa.text(
            dedent(
                """
                CREATE OR REPLACE FUNCTION public.trigger_set_default_buffer_geometry()
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
                
                BEGIN
                    SELECT ogd.geometry
                    INTO v_object_geom
                    FROM public.urban_objects_data uod
                    JOIN public.object_geometries_data ogd ON uod.object_geometry_id = ogd.object_geometry_id
                    WHERE uod.urban_object_id = NEW.urban_object_id;
                
                    IF v_object_geom IS NULL THEN
                        RAISE EXCEPTION 'Could not find geometry for urban_object_id=%', NEW.urban_object_id;
                    END IF;
                
                
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
                FROM public.urban_objects_data uod
                LEFT JOIN public.physical_objects_data pod ON uod.physical_object_id = pod.physical_object_id
                LEFT JOIN public.services_data sd ON uod.service_id = sd.service_id
                WHERE uod.urban_object_id = NEW.urban_object_id;
                
                
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
                
                        END IF;
                
                        RETURN NEW;
                    END;
                    $function$
                ;
                """
            )
        )
    )
