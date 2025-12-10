"""Database layer exceptions for urban_api are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class DBError(UrbanApiError):
    """Base exception for DB errors."""


class UniqueConstraintError(DBError):
    """Exception to raise when requested entity with the same parameters was found in the database."""

    def __init__(self, detail: str):
        """Construct from entity (table) name and list of parameters."""
        self.detail = detail


class DependencyNotFound(DBError):
    """Exception to raise when foreign entity was not found in the database."""

    def __init__(self, constraint: str):
        """Construct from entity (table) name and list of parameters."""
        self.constraint = constraint


class InvalidValueError(DBError):
    """Exception to raise when invalid value (not geometry) was passed."""

    def __init__(self, detail: str):
        """Construct from entity (table) name and list of parameters."""
        self.detail = detail


class CustomTriggerError(DBError):
    """Exception to raise when requested entity with the same parameters was found in the database."""

    def __init__(self, detail: str):
        """Construct from entity (table) name and list of parameters."""
        self.detail = detail
