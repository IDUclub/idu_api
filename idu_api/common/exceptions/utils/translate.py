import re
from typing import Any

from asyncpg import exceptions as apg_exc
from sqlalchemy.exc import DBAPIError, IntegrityError

from idu_api.common.exceptions import IduApiError
from idu_api.common.exceptions.logic.db import (
    DependencyNotFound,
    InvalidValueError,
    UniqueConstraintError, CustomTriggerError,
)

# SQLSTATE codes
SQLSTATE_UNIQUE = "23505"
SQLSTATE_FK = "23503"

# Keywords to detect unique / fk violations (fallback: EN + RU)
_UNIQUE_KEYWORDS = [
    "duplicate key",
    "violates unique constraint",
    "already exists",
    "unique constraint",
    "duplicate",
    "повторяющ",
    "уже существует",
    "уже есть",
    "ограничени",
    "уникальн",
]
_FK_KEYWORDS = [
    "violates foreign key constraint",
    "foreign key",
    "is not present in table",
    "references",
    "внешн",
    "не существует в таблице",
    "отсутствует в таблице",
]


def _decode_if_bytes(val: Any) -> str | None:
    """Decode bytes/bytearray to str with common encodings, else return str(val)."""
    if val is None:
        return None
    if isinstance(val, (bytes, bytearray)):
        for enc in ("utf-8", "latin-1", "cp1251"):
            try:
                return val.decode(enc)
            except Exception:
                continue
        return val.decode(errors="ignore")
    return str(val)


def _extract_info(exc: Exception) -> tuple[list[str], list[str], list[str], list[str]]:
    """Extracts texts, sqlstates, details, and statements from nested exceptions.
    Returns (texts, sqlstates, details, statements)."""

    texts, sqlstates, details, statements = [], [], [], []
    visited = set()
    queue: list[Any] = [
        exc,
        getattr(exc, "orig", None),
        getattr(exc, "__cause__", None),
        getattr(exc, "__context__", None),
    ]

    while queue:
        cur = queue.pop(0)
        if cur is None or id(cur) in visited:
            continue
        visited.add(id(cur))

        # string repr
        try:
            s = _decode_if_bytes(cur)
            if s:
                texts.append(s)
        except Exception:
            pass

        # asyncpg specifics
        if isinstance(cur, apg_exc.PostgresError):
            ss = getattr(cur, "sqlstate", None) or getattr(cur, "code", None) or getattr(cur, "pgcode", None)
            if ss:
                sqlstates.append(_decode_if_bytes(ss))
            det = getattr(cur, "detail", None) or getattr(cur, "message", None)
            if det:
                det = det.replace('"', "'") if det else None
                details.append(_decode_if_bytes(det))
            q = getattr(cur, "query", None)
            if q:
                statements.append(_decode_if_bytes(q))

        # sqlalchemy DBAPIError specifics
        if isinstance(cur, DBAPIError):
            if cur.statement:
                statements.append(_decode_if_bytes(cur.statement))

        # go deeper if cur has common nested attributes
        for attr in ("orig", "__cause__", "__context__"):
            try:
                v = getattr(cur, attr, None)
            except Exception:
                v = None
            if v is not None:
                queue.append(v)

    return texts, sqlstates, details, statements


def translate_db_error(exc: Exception) -> IduApiError:
    """
    Translate SQLAlchemy/asyncpg/Postgres exceptions into domain-specific IduApiError.
    Strategy: type -> sqlstate -> keywords.
    """
    # Already domain error
    if isinstance(exc, IduApiError):
        return exc

    # Integrity / DB constraint errors
    if isinstance(exc, (IntegrityError, DBAPIError)):
        texts, sqlstates, details, _ = _extract_info(exc)
        combined_text = " ".join(texts).lower()
        detail = details[0] if details else None

        # sqlstate check
        for ss in sqlstates:
            if ss == SQLSTATE_UNIQUE:
                return UniqueConstraintError(detail)
            if ss == SQLSTATE_FK:
                return DependencyNotFound(detail)
            if ss.startswith("P"):
                return CustomTriggerError(detail)

        # fallback by keywords
        if any(k in combined_text for k in _UNIQUE_KEYWORDS):
            return UniqueConstraintError(detail)
        if any(k in combined_text for k in _FK_KEYWORDS):
            return DependencyNotFound(detail)
        if any(k in combined_text for k in ("int32", "out of range")):
            return InvalidValueError("Значение выходит за диапазон INTEGER (int32).")

    # Default fallback
    return IduApiError()


def extract_sql(exc: Exception, max_len: int = 500) -> str | None:
    """Returns SQL statement from SQLAlchemy error if exists."""
    _, _, _, statements = _extract_info(exc)
    statement = statements[0] if statements else None

    return statement[:max_len] + "..."
