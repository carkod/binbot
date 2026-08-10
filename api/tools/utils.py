from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


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
