"""All enums are defined here."""

from enum import Enum


class DateType(str, Enum):
    """Granularity types for date-based aggregation."""

    YEAR = "year"
    HALF_YEAR = "half_year"
    QUARTER = "quarter"
    MONTH = "month"
    DAY = "day"


class ValueType(str, Enum):
    """Types of values used in calculations and reporting."""

    REAL = "real"
    TARGET = "target"
    FORECAST = "forecast"


class Ordering(str, Enum):
    """Sort direction for query results."""

    ASC = "asc"
    DESC = "desc"


class OrderByField(str, Enum):
    """Fields available for ordering query results."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class NormativeType(str, Enum):
    """Source type of normative value in hierarchy."""

    SELF = "self"
    PARENT = "parent"
    GLOBAL = "global"


class InfrastructureType(str, Enum):
    """Infrastructure classification type."""

    BASIC = "basic"
    ADDITIONAL = "additional"
    COMFORT = "comfort"


class ProjectType(str, Enum):
    """Project classification type."""

    COMMON = "common"
    CITY = "city"


class ProjectPhase(str, Enum):
    """Lifecycle phases of a project."""

    INVESTMENT = "investment"
    PRE_DESIGN = "pre_design"
    DESIGN = "design"
    CONSTRUCTION = "construction"
    OPERATION = "operation"
    DECOMMISSION = "decommission"
