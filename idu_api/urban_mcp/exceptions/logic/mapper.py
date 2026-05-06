"""Mapper from logic exceptions to MCP error is defined here."""

from mcp import ErrorData, McpError

from idu_api.urban_api.exceptions.logic import common, db, projects, users
from idu_api.urban_mcp.exceptions.mapper import ExceptionMapper


def _get_mcp_error(code: int, message: str) -> McpError:
    """Create MCP error with a standard structure."""
    return McpError(ErrorData(code=code, message=message))


def register_exceptions(mapper: ExceptionMapper) -> None:
    """Register domain and database exceptions to MCP errors."""
    mapper.register_func(
        common.TooManyObjectsError,
        lambda exc: _get_mcp_error(
            code=-32602,
            message=f"Вернулось слишком много объектов: {exc.objects}"
            + (f", хотя лимит – {exc.limit}" if exc.limit is not None else "")
            + ".",
        ),
    )
    mapper.register_func(
        common.EntityNotFoundById,
        lambda exc: _get_mcp_error(
            code=-32001,
            message=f"Сущность '{exc.entity}' с (id={exc.requested_id}) не найдена.",
        ),
    )
    mapper.register_func(
        common.EntitiesNotFoundByIds,
        lambda exc: _get_mcp_error(
            code=-32001,
            message=f"По крайней мере один {exc.entity} из переданных id не найден.",
        ),
    )
    mapper.register_func(
        common.EntityNotFoundByParams,
        lambda exc: _get_mcp_error(
            code=-32001,
            message=f"Сущность '{exc.entity}' с такими параметрами {exc.params} не найдена.",
        ),
    )
    mapper.register_func(
        common.EntityAlreadyExists,
        lambda exc: _get_mcp_error(
            code=-32602,
            message=f"Сущность '{exc.entity}' с такими параметрами {exc.params} уже существует.",
        ),
    )
    mapper.register_func(
        common.EntityAlreadyEdited,
        lambda exc: _get_mcp_error(
            code=-32602,
            message=f"Сущность '{exc.entity}' уже изменена или удалена для этого сценария (id={exc.scenario_id}).",
        ),
    )

    mapper.register_func(db.UniqueConstraintError, lambda exc: _get_mcp_error(code=-32602, message=exc.detail))
    mapper.register_func(db.DependencyNotFound, lambda exc: _get_mcp_error(code=-32001, message=exc.constraint))
    mapper.register_func(db.InvalidValueError, lambda exc: _get_mcp_error(code=-32602, message=exc.detail))
    mapper.register_func(db.CustomTriggerError, lambda exc: _get_mcp_error(code=-32602, message=exc.detail))

    mapper.register_simple(db.DBError, -32602, "Exception occurred at database request")
    mapper.register_simple(
        projects.NotAllowedInRegionalScenario,
        -32602,
        "Этот метод недоступен в РЕГИОНАЛЬНОМ сценарии. Передайте идентификатор сценария ПРОЕКТА.",
    )
    mapper.register_simple(
        projects.NotAllowedInProjectScenario,
        -32602,
        "Этот метод недоступен в сценарии ПРОЕКТА. Укажите идентификатор РЕГИОНАЛЬНОГО сценария.",
    )
    mapper.register_simple(
        projects.NotAllowedInRegionalProject,
        -32602,
        "Этот метод недоступен в РЕГИОНАЛЬНОМ проекте. Укажите идентификатор ОБЫЧНОГО проекта.",
    )

    mapper.register_simple(users.NotAuthorizedError, -31001, "Для доступа необходима авторизация.")
    mapper.register_func(users.AuthorizationError, lambda exc: _get_mcp_error(code=-31002, message=exc.reason))
    mapper.register_func(
        users.AccessDeniedError,
        lambda exc: _get_mcp_error(
            code=-30001,
            message=f"Доступ к '{exc.entity}' с (id)={exc.requested_id} запрещён.",
        ),
    )
