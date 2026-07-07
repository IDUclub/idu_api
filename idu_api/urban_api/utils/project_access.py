"""Project access role helpers are defined here."""

from typing import Any

from idu_api.urban_api.dto import UserDTO

PROJECTS_READ_ROLE = "projects:read"
PROJECTS_WRITE_ROLE = "projects:write"


def has_projects_write_role(user: UserDTO | None) -> bool:
    """Return whether user has global write access to projects."""

    return user is not None and PROJECTS_WRITE_ROLE in user.roles


def has_projects_read_role(user: UserDTO | None) -> bool:
    """Return whether user has global read access to projects."""

    return user is not None and (PROJECTS_READ_ROLE in user.roles or has_projects_write_role(user))


def can_read_any_project(user: UserDTO | None) -> bool:
    """Return whether user can read projects regardless of ownership or public flag."""

    return user is not None and (user.is_superuser or has_projects_read_role(user))


def can_write_any_project(user: UserDTO | None) -> bool:
    """Return whether user can write projects regardless of ownership."""

    return user is not None and (user.is_superuser or has_projects_write_role(user))


def can_read_project(project: Any, user: UserDTO | None) -> bool:
    """Return whether user can read a specific project-like row."""

    if project is None:
        return False
    if user is None:
        return bool(getattr(project, "public", False))
    return (
        getattr(project, "user_id", None) == user.id
        or bool(getattr(project, "public", False))
        or can_read_any_project(user)
    )


def can_write_project(project: Any, user: UserDTO | None) -> bool:
    """Return whether user can mutate a specific project-like row."""

    if project is None:
        return False
    if user is None:
        return False
    return getattr(project, "user_id", None) == user.id or can_write_any_project(user)


def can_access_project(project: Any, user: UserDTO | None, to_edit: bool = False) -> bool:
    """Return whether user has read or write access to a specific project-like row."""

    return can_write_project(project, user) if to_edit else can_read_project(project, user)


def can_use_project_user_id(user: UserDTO | None, user_id: str, to_edit: bool = False) -> bool:
    """Return whether user can act on behalf of another project owner identifier."""

    if user is None:
        return False
    if user.id == user_id:
        return True
    return can_write_any_project(user) if to_edit else can_read_any_project(user)
