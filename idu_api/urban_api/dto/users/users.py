"""User DTO is defined here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserDTO:
    """User data transfer object"""

    id: str
    username: str
    roles: list[str]
    is_superuser: bool
    azp: str

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return self.id
