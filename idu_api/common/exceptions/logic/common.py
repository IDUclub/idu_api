"""
Exceptions connected with entities in urban_db are defined here.
"""

from fastapi import status

from idu_api.common.exceptions import IduApiError


class TooManyObjectsError(IduApiError):
    """Exception to raise when number of objects to be returned is too big."""

    def __init__(self, number_of_objects: int, limit: int | None = None):
        """Construct from actual number of objects and set limit."""
        self.objects = number_of_objects
        self.limit = limit
        super().__init__()

    def __str__(self) -> str:
        return (
            f"Вернулось слишком много объектов. Их количество – {self.objects}" + f", хотя лимит – {self.limit}"
            if self.limit is not None
            else ""
        )

    def get_status_code(self) -> int:
        """Return '400 Bad Request' status code."""
        return status.HTTP_400_BAD_REQUEST


class EntityNotFoundById(IduApiError):
    """
    Exception to raise when requested entity was not found in the database by the identifier.
    """

    def __init__(self, requested_id: int, entity: str):
        """
        Construct from requested identifier and entity (table) name.
        """
        self.requested_id = requested_id
        self.entity = entity
        super().__init__()

    def __str__(self) -> str:
        return f"Сущность '{self.entity}' с (id)=({self.requested_id}) не найдена."

    def get_status_code(self) -> int:
        """
        Return '404 Not found' status code.
        """
        return status.HTTP_404_NOT_FOUND


class EntitiesNotFoundByIds(IduApiError):
    """
    Exception to raise when requested entity was not found in the database by the list of identifiers.
    """

    def __init__(self, entity: str):
        """
        Construct from entity (table) name.
        """
        self.entity = entity
        super().__init__()

    def __str__(self) -> str:
        return f"По крайней мере, один '{self.entity}' из переданных id не найден."

    def get_status_code(self) -> int:
        """
        Return '404 Not found' status code.
        """
        return status.HTTP_404_NOT_FOUND


class EntityNotFoundByParams(IduApiError):
    """
    Exception to raise when requested entity was not found in the database by the identifier.
    """

    def __init__(self, entity: str, *args):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.entity = entity
        self.params = tuple(args)
        super().__init__()

    def __str__(self) -> str:
        return f"Сущность '{self.entity}' с такими параметрами: {self.params} не найдена."

    def get_status_code(self) -> int:
        """
        Return '404 Not found' status code.
        """
        return status.HTTP_404_NOT_FOUND


class EntityAlreadyExists(IduApiError):
    """
    Exception to raise when requested entity with the same parameters was found in the database.
    """

    def __init__(self, entity: str, *args):
        """
        Construct from entity (table) name and list of parameters.
        """
        self.entity = entity
        self.params = tuple(args)
        super().__init__()

    def __str__(self) -> str:
        return f"Сущность '{self.entity}' с такими параметрами: {self.params} – уже существует."

    def get_status_code(self) -> int:
        """
        Return '409 Conflict' status code.
        """
        return status.HTTP_409_CONFLICT


class EntityAlreadyEdited(IduApiError):
    """
    Exception to raise when requested entity with the same parameters has been edited or deleted from the database.
    """

    def __init__(self, entity: str, scenario_id: int):
        """
        Construct from scenario identifier and entity (table) name.
        """
        self.entity = entity
        self.scenario_id = scenario_id
        super().__init__()

    def __str__(self) -> str:
        return f"Сущность '{self.entity}' уже изменен или удален для этого сценария (id)=({self.scenario_id})."

    def get_status_code(self) -> int:
        """
        Return '409 Conflict' status code.
        """
        return status.HTTP_409_CONFLICT
