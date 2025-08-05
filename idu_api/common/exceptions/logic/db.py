from starlette import status

from idu_api.common.exceptions import IduApiError


class UniqueConstraintError(IduApiError):
    """
    Exception to raise when requested entity with the same parameters was found in the database.
    """

    def __init__(self, detail: str):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.detail = detail
        super().__init__()

    def __str__(self) -> str:
        return self.detail

    def get_status_code(self) -> int:
        """
        Return '409 Conflict' status code.
        """
        return status.HTTP_409_CONFLICT


class DependencyNotFound(IduApiError):
    """
    Exception to raise when foreign entity was not found in the database.
    """

    def __init__(self, constraint: str):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.constraint = constraint
        super().__init__()

    def __str__(self) -> str:
        return self.constraint

    def get_status_code(self) -> int:
        """
        Return '404 Not found' status code.
        """
        return status.HTTP_404_NOT_FOUND


class InvalidValueError(IduApiError):
    """Exception to raise when invalid value (not geometry) was passed."""

    def __init__(self, detail: str):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.detail = detail
        super().__init__()

    def __str__(self) -> str:
        return self.detail

    def get_status_code(self) -> int:
        """Return '400 Bad Request' status code."""
        return status.HTTP_400_BAD_REQUEST


class CustomTriggerError(IduApiError):
    """
    Exception to raise when requested entity with the same parameters was found in the database.
    """

    def __init__(self, detail: str):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.detail = detail
        super().__init__()

    def __str__(self) -> str:
        return self.detail

    def get_status_code(self) -> int:
        """
        Return '400 Bad Request' status code.
        """
        return status.HTTP_400_BAD_REQUEST
