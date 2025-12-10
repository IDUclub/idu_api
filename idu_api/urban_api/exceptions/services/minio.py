"""Exceptions connected with image and Pillow library are defined here."""

from idu_api.urban_api.exceptions import UrbanApiError


class InvalidImageError(UrbanApiError):
    """Exception to raise when user upload invalid image."""

    def __init__(self, project_id: int):
        """Construct from requested project identifier."""
        super().__init__()
        self.project_id = project_id


class FileNotFound(UrbanApiError):
    """Exception to raise when file with given name was not found for specified project."""

    def __init__(self, project_id: int, filename: str):
        """Construct from requested project and image identifiers."""
        super().__init__()
        self.project_id = project_id
        self.filename = filename
