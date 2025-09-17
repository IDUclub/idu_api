"""
Exceptions connected with entities in urban_db are defined here.
"""

from fastapi import status

from idu_api.common.exceptions import IduApiError


class NotAllowedInRegionalScenario(IduApiError):
    """
    Exception to raise when attempting to access entities that can only be retrieved in a project scenario only.
    """

    def __str__(self) -> str:
        return "Этот метод недоступен в РЕГИОНАЛЬНОМ сценарии. Передайте идентификатор сценария ПРОЕКТА."

    def get_status_code(self) -> int:
        """
        Return '400 Bad Request' status code.
        """
        return status.HTTP_400_BAD_REQUEST


class NotAllowedInProjectScenario(IduApiError):
    """
    Exception to raise when attempting to access entities that can only be retrieved in a regional scenario only.
    """

    def __str__(self) -> str:
        return "Этот метод недоступен в сценарии ПРОЕКТА. Укажите идентификатор РЕГИОНАЛЬНОГО сценария."

    def get_status_code(self) -> int:
        """
        Return '400 Bad Request' status code.
        """
        return status.HTTP_400_BAD_REQUEST


class NotAllowedInRegionalProject(IduApiError):
    """
    Exception to raise when attempting to access entities that can only be retrieved in a non-regional project only.
    """

    def __str__(self) -> str:
        return "Этот метод недоступен в РЕГИОНАЛЬНОМ проекте. Укажите идентификатор ОБЫЧНОГО проекта."

    def get_status_code(self) -> int:
        """
        Return '400 Bad Request' status code.
        """
        return status.HTTP_400_BAD_REQUEST


class InvalidBaseScenario(IduApiError):
    """
    Exception to raise when attempting to change base scenario by editing itself.
    """

    def __str__(self) -> str:
        return (
            "Если вы хотите создать новый базовый сценарий, измените тот, который должен стать базовым, а не текущий."
        )

    def get_status_code(self) -> int:
        """
        Return '400 Bad Request' status code.
        """
        return status.HTTP_400_BAD_REQUEST
