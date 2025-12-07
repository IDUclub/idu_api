"""Exception mapper registration of available exceptions is located here."""

from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette import status

from idu_api.common.exceptions.base import IduApiError
from idu_api.common.exceptions.mapper import ExceptionMapper

from .base import UrbanApiError
from .logic.mapper import register_exceptions as register_logic_errors
from .services.mapper import register_exceptions as register_services_errors
from .utils.translate import translate_db_constraint_error


def register_exceptions(mapper: ExceptionMapper) -> None:
    mapper.register_simple(IduApiError, status.HTTP_500_INTERNAL_SERVER_ERROR, "Unexpected error happened in IDU API")
    mapper.register_simple(
        UrbanApiError, status.HTTP_500_INTERNAL_SERVER_ERROR, "Unexpected error happened in Urban API"
    )

    register_logic_errors(mapper)
    register_services_errors(mapper)

    mapper.register_func(IntegrityError, lambda exc: mapper.apply(translate_db_constraint_error(exc)))
    mapper.register_func(DBAPIError, lambda exc: mapper.apply(translate_db_constraint_error(exc)))
