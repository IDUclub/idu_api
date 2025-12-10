"""Base UrbanAPI error is defined here."""


class UrbanApiError(Exception):
    """
    Base Urban API exception to inherit from.
    """

    def __str__(self) -> str:
        return f"Unexpected error happened in Urban API ({type(self).__qualname__})"
