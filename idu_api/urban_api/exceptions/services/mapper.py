"""Mapper from logic exceptions to JSONResponses is defined here."""

from fastapi import status
from fastapi.responses import JSONResponse

from idu_api.common.exceptions.mapper import ExceptionMapper

from . import auth, external, minio


def _get_response(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse({"error": error, "detail": detail}, status_code=status_code)


def register_exceptions(mapper: ExceptionMapper) -> None:
    mapper.register_simple(auth.AuthTokenExpiredError, status.HTTP_403_FORBIDDEN, "Срок действия токена истёк.")
    mapper.register_simple(auth.JWTDecodeError, status.HTTP_403_FORBIDDEN, "Ошибка декодирования JWT.")
    mapper.register_simple(auth.InvalidTokenSignature, status.HTTP_403_FORBIDDEN, "Недопустимая подпись токена.")

    mapper.register_func(
        external.ExternalServiceResponseError,
        lambda exc: _get_response(
            exc.status_code,
            "Invalid External Service Response",
            f"Ошибка в ответе внешнего сервиса '{exc.service}': {exc.error}",
        ),
    )
    mapper.register_func(
        external.ExternalServiceUnavailable,
        lambda exc: _get_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "External Service Unavailable",
            f"Внешний сервис ({exc.service}) недоступен.",
        ),
    )

    mapper.register_func(
        minio.InvalidImageError,
        lambda exc: _get_response(
            status.HTTP_400_BAD_REQUEST,
            "Invalid Image Error Unavailable",
            f"Было загружено неверное изображение для проекта с идентификатором = {exc.project_id}.",
        ),
    )
    mapper.register_func(
        minio.FileNotFound,
        lambda exc: _get_response(
            status.HTTP_404_NOT_FOUND,
            "File Not Found",
            f"Файл `{exc.filename}` не найден для проекта с идентификатором = {exc.project_id}.",
        ),
    )
