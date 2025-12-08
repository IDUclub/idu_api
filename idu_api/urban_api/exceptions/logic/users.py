"""
Exceptions connected with user's logic are defined here.
"""

from idu_api.urban_api.exceptions import UrbanApiError


class AccessDeniedError(UrbanApiError):
    """Exception to raise when you do not have access rights to a resource."""

    def __init__(self, requested_id: int, entity: str):
        """Construct from requested identifier and entity (table) name."""
        super().__init__()
        self.requested_id = requested_id
        self.entity = entity
