from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from uuid import UUID

from pybinbot import BotModel
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Session

from api.databases.utils import get_db_session


_entry_lock = RLock()


def datetime_to_iso(value: datetime | str) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.isoformat(sep=" ", timespec="seconds")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def coerce_millisecond_timestamp(value: object) -> int | None:
    """Return a numeric timestamp as integer milliseconds when possible."""
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(value)
        except ValueError:
            return None
    return None


# JSONB on Postgres, plain JSON on SQLite/other dialects (so tests still work).
JsonVariant = JSON().with_variant(JSONB(), "postgresql")


@contextmanager
def submission_guard(bot_id: UUID) -> Generator[tuple[BotModel, Session]]:
    # This module is also imported by table definitions, so defer CRUD imports.
    from api.databases.crud.bot_crud import BotTableCrud

    # One exchange account is configured for this installation. The local lock
    # also serializes SQLite tests; PostgreSQL coordinates separate processes.
    with _entry_lock, get_db_session() as session:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(738124901)"))
        bot = BotModel.dump_from_table(
            BotTableCrud(session).get_one(bot_id=str(bot_id))
        )
        yield bot, session
