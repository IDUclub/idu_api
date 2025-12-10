"""Exceptions connected with entities in urban_db are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class TooManyObjectsError(UrbanApiError):
    """Exception to raise when number of objects to be returned is too big."""

    def __init__(self, number_of_objects: int, limit: int | None = None):
        """Construct from actual number of objects and set limit."""
        super().__init__()
        self.objects = number_of_objects
        self.limit = limit


class EntityNotFoundById(UrbanApiError):
    """Exception to raise when requested entity was not found in the database by the identifier."""

    def __init__(self, requested_id: int, entity: str):
        """Construct from requested identifier and entity (table) name."""
        super().__init__()
        self.requested_id = requested_id
        self.entity = entity


class EntitiesNotFoundByIds(UrbanApiError):
    """Exception to raise when requested entity was not found in the database by the list of identifiers."""

    def __init__(self, entity: str):
        """Construct from entity (table) name."""
        super().__init__()
        self.entity = entity


class EntityNotFoundByParams(UrbanApiError):
    """Exception to raise when requested entity was not found in the database by the identifier."""

    def __init__(self, entity: str, *args):
        """Construct from entity (table) name and list of parameters."""
        super().__init__()
        self.entity = entity
        self.params = tuple(args)


class EntityAlreadyExists(UrbanApiError):
    """Exception to raise when requested entity with the same parameters was found in the database."""

    def __init__(self, entity: str, *args):
        """Construct from entity (table) name and list of parameters."""
        super().__init__()
        self.entity = entity
        self.params = tuple(args)


class EntityAlreadyEdited(UrbanApiError):
    """
    Exception to raise when requested entity with the same parameters has been edited or deleted from the database.
    """

    def __init__(self, entity: str, scenario_id: int):
        """Construct from scenario identifier and entity (table) name."""
        super().__init__()
        self.entity = entity
        self.scenario_id = scenario_id
