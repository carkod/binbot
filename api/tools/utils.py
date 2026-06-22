from datetime import datetime, timezone


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
