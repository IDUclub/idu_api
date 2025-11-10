"""Bindings data tables are defined here."""

from sqlalchemy import Column, Float, Integer, Table
from sqlalchemy.sql.schema import ForeignKeyConstraint, PrimaryKeyConstraint

from idu_api.common.db import metadata

territory_indicators_binds_data = Table(
    "territory_indicators_binds_data",
    metadata,
    Column("indicator_id", Integer(), nullable=False),
    Column("territory_id", Integer(), nullable=False),
    Column("level", Integer(), nullable=False),
    Column("min_value", Float(precision=53), nullable=False),
    Column("max_value", Float(precision=53), nullable=False),
    ForeignKeyConstraint(
        ["indicator_id"],
        ["indicators_dict.indicator_id"],
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["territory_id"],
        ["territories_data.territory_id"],
        ondelete="CASCADE",
    ),
    PrimaryKeyConstraint("indicator_id", "territory_id", "level"),
    schema="tech",
)

"""
Territory Indicators Binds:
- indicator_id int fk pk
- territory_id int fk pk
- level int pk
- min_value float(53)
- max_value float(53)
"""
