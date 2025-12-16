"""Projects cadastres data table is defined here."""

from typing import Callable

from geoalchemy2.types import Geometry
from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    Sequence,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from idu_api.common.db import metadata
from idu_api.common.db.entities.projects.projects import projects_data

func: Callable

project_cadastre_id_seq = Sequence("project_id_seq", schema="user_projects")

projects_cadastres_data = Table(
    "projects_cadastres_data",
    metadata,
    Column("project_cadastre_id", Integer, primary_key=True, server_default=project_cadastre_id_seq.next_value()),
    Column(
        "project_id",
        Integer,
        ForeignKey(projects_data.c.project_id),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "geometry",
        Geometry(spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry"),
        nullable=False,
    ),
    Column(
        "centre_point",
        Geometry("POINT", spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry"),
        nullable=False,
    ),
    Column("properties", JSONB(astext_type=Text()), server_default=text("'{}'::jsonb"), nullable=False),
    Column("area", Float(precision=53), nullable=True),
    Column("cad_num", String(), nullable=True),
    Column("cost_value", Float(precision=53), nullable=True),
    Column("land_record_area", Float(precision=53), nullable=True),
    Column("land_record_category_type", String(), nullable=True),
    Column("ownership_type", String(), nullable=True),
    Column("permitted_use_established_by_document", String(), nullable=True),
    Column("quarter_cad_number", String(), nullable=True),
    Column("readable_address", Text(), nullable=True),
    Column("specified_area", Float(precision=53), nullable=True),
    Column("status", String(), nullable=True),
    Column("zone_pzz", String(), nullable=True),
    Column("possible_pzz_vri", String(), nullable=True),
    Column("possible_vri_list", Text(), nullable=True),
    Column("similarity_score", Float(precision=53), nullable=True),
    schema="user_projects",
)

"""
Project cadastre data:
- project_id foreign key int
- geometry geom
- centre_point geom
- properties jsonb
- area float
- cad_num str
- cost_value float
- land_record_area float
- land_record_category_type str
- ownership_type str
- permitted_use_established_by_document str
- quarter_cad_number str
- readable_address str
- specified_area float
- status str
- zone_pzz str
- possible_pzz_vri str
- possible_vri_list str
- similarity_score float
"""
