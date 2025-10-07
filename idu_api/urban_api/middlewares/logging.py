import time
import uuid
from http.client import HTTPException

import structlog
from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from idu_api.common.exceptions import IduApiError
from idu_api.common.exceptions.utils.translate import extract_sql, translate_db_error
from idu_api.urban_api.dto.users.users import UserDTO
from idu_api.urban_api.prometheus import metrics
from idu_api.urban_api.utils.logging import get_handler_from_path


class LoggingMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware for logging requests. Using `state.user` data and `state.logger` to log details."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4()
        logger: structlog.stdlib.BoundLogger = request.app.state.logger
        logger = logger.bind(request_id=str(request_id))
        request.state.logger = logger
        user: UserDTO | None = request.state.user

        await logger.ainfo(
            "handling request",
            client=request.client.host,
            path_params=request.path_params,
            method=request.method,
            url=str(request.url),
            user=user,
        )

        path_for_metric = get_handler_from_path(request.url.path)

        time_begin = time.monotonic_ns()
        try:
            result = await call_next(request)

            time_finish = time.monotonic_ns()
            duration_seconds = (time_finish - time_begin) / 1e9
            await logger.ainfo("request handled successfully", time_consumed=round(duration_seconds, 3))
            metrics.SUCCESS_COUNTER.labels(
                method=request.method, path=path_for_metric, status_code=result.status_code
            ).inc(1)
            return result
        except Exception as exc:
            time_finish = time.monotonic_ns()
            duration_seconds = (time_finish - time_begin) / 1e9

            if isinstance(exc, (IduApiError, HTTPException)):
                await logger.aerror(
                    "failed to handle request", time_consumed=round(duration_seconds, 3), error_type=type(exc).__name__
                )
            elif isinstance(exc, SQLAlchemyError):
                translated = translate_db_error(exc)
                sql = extract_sql(exc)
                log_func = logger.aexception if type(exc) is IduApiError else logger.aerror
                await log_func(
                    "failed to handle request",
                    time_consumed=round(duration_seconds, 3),
                    error_type=type(translated).__name__,
                    sql=sql,
                )
            else:
                await logger.aexception(
                    "failed to handle request", time_consumed=round(duration_seconds, 3), error_type=type(exc).__name__
                )
            raise
        finally:
            metrics.REQUESTS_COUNTER.labels(
                method=request.method, path=path_for_metric, is_user_set=user is not None
            ).inc(1)
            metrics.REQUEST_TIME.labels(method=request.method, path=path_for_metric).observe(duration_seconds)
