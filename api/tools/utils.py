from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# JSONB on Postgres, plain JSON on SQLite/other dialects (so tests still work).
JsonVariant = JSON().with_variant(JSONB(), "postgresql")
