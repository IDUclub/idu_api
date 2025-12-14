"""Mapper from logic exceptions to JSONResponses is defined here."""

from fastapi import status
from fastapi.responses import JSONResponse

from idu_api.common.exceptions.mapper import ExceptionMapper

from . import common, db, projects, users


def _get_response(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse({"error": error, "detail": detail}, status_code=status_code)


def register_exceptions(mapper: ExceptionMapper) -> None:
    mapper.register_func(
        common.TooManyObjectsError,
        lambda exc: _get_response(
            status.HTTP_400_BAD_REQUEST,
            "Too Many Objects",
            f"Вернулось слишком много объектов: {exc.objects}"
            + (f", хотя лимит – {exc.limit}" if exc.limit is not None else "")
            + ".",
        ),
    )
    mapper.register_func(
        common.EntityNotFoundById,
        lambda exc: _get_response(
            status.HTTP_404_NOT_FOUND,
            "Entitiy not found by IDs",
            f"Сущность '{exc.entity}' с (id={exc.requested_id}) не найдена.",
        ),
    )
    mapper.register_func(
        common.EntitiesNotFoundByIds,
        lambda exc: _get_response(
            status.HTTP_404_NOT_FOUND,
            "Entities not found by IDs",
            f"По крайней мере один (id={exc.entity}) из переданных id не найден в БД.",
        ),
    )
    mapper.register_func(
        common.EntityNotFoundByParams,
        lambda exc: _get_response(
            status.HTTP_404_NOT_FOUND,
            "Entitiy not found by parameters",
            f"Сущность '{exc.entity}' с такими параметрами ({exc.params}) не найдена.",
        ),
    )
    mapper.register_func(
        common.EntityAlreadyExists,
        lambda exc: _get_response(
            status.HTTP_409_CONFLICT,
            "Entitiy already exists",
            f"Сущность '{exc.entity}' с такими параметрами ({exc.params}) уже существует.",
        ),
    )
    mapper.register_func(
        common.EntityAlreadyEdited,
        lambda exc: _get_response(
            status.HTTP_409_CONFLICT,
            "Entitiy already edited",
            f"Сущность '{exc.entity}' уже изменена или удалена для этого сценария (id={exc.scenario_id}).",
        ),
    )

    mapper.register_func(
        db.UniqueConstraintError,
        lambda exc: _get_response(status.HTTP_409_CONFLICT, "Unique Constraint Error", exc.detail),
    )
    mapper.register_func(
        db.DependencyNotFound,
        lambda exc: _get_response(status.HTTP_404_NOT_FOUND, "Dependency Not Found", exc.constraint),
    )
    mapper.register_func(
        db.InvalidValueError,
        lambda exc: _get_response(status.HTTP_400_BAD_REQUEST, "Invalid Value", exc.detail),
    )
    mapper.register_func(
        db.CustomTriggerError,
        lambda exc: _get_response(status.HTTP_400_BAD_REQUEST, "Invalid Value", exc.detail),
    )
    mapper.register_simple(db.DBError, 500, "Exception occurred at database request")

    mapper.register_simple(
        projects.NotAllowedInRegionalScenario,
        status.HTTP_400_BAD_REQUEST,
        "Этот метод недоступен в РЕГИОНАЛЬНОМ сценарии. Передайте идентификатор сценария ПРОЕКТА.",
    )
    mapper.register_simple(
        projects.NotAllowedInProjectScenario,
        status.HTTP_400_BAD_REQUEST,
        "Этот метод недоступен в сценарии ПРОЕКТА. Укажите идентификатор РЕГИОНАЛЬНОГО сценария.",
    )
    mapper.register_simple(
        projects.NotAllowedInRegionalProject,
        status.HTTP_400_BAD_REQUEST,
        "Этот метод недоступен в РЕГИОНАЛЬНОМ проекте. Укажите идентификатор ОБЫЧНОГО проекта.",
    )
    mapper.register_simple(
        projects.InvalidBaseScenario,
        status.HTTP_400_BAD_REQUEST,
        "Если вы хотите создать новый базовый сценарий, измените тот, который должен стать базовым, а не текущий.",
    )

    mapper.register_simple(
        users.NotAuthorizedError, status.HTTP_401_UNAUTHORIZED, "Для доступа необходима авторизация."
    )
    mapper.register_func(
        users.AuthorizationError,
        lambda exc: _get_response(
            status.HTTP_403_FORBIDDEN,
            "AuthorizationError",
            exc.reason,
        ),
    )
    mapper.register_func(
        users.AccessDeniedError,
        lambda exc: _get_response(
            status.HTTP_403_FORBIDDEN,
            "AccessDeniedError",
            f"Доступ к '{exc.entity}' с (id)={exc.requested_id} запрещён.",
        ),
    )
