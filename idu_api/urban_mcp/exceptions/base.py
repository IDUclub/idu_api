"""Base Urban MCP error is defined here."""


class UrbanMCPError(Exception):
    """Base Urban MCP exception to inherit from."""

    def __str__(self) -> str:
        return f"Unexpected error happened in Urban MCP ({type(self).__qualname__})"
