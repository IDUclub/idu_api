"""Exceptions connected with entities in urban_db are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class NotAllowedInRegionalScenario(UrbanApiError):
    """Exception to raise when attempting to access entities that can only be retrieved in a project scenario only."""


class NotAllowedInProjectScenario(UrbanApiError):
    """Exception to raise when attempting to access entities that can only be retrieved in a regional scenario only."""


class NotAllowedInRegionalProject(UrbanApiError):
    """
    Exception to raise when attempting to access entities that can only be retrieved in a non-regional project only.
    """


class InvalidBaseScenario(UrbanApiError):
    """Exception to raise when attempting to change base scenario by editing itself."""
