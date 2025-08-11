import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple


def cache(
    ttl_seconds: int = 3600,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Simple in-process TTL cache decorator (per process).
    Caches function results by args/kwargs for ttl_seconds.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        store: Dict[
            Tuple[Tuple[Any, ...], Tuple[Tuple[str, Any], ...]], Tuple[float, Any]
        ] = {}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in store:
                expiry, value = store[key]
                if now < expiry:
                    return value
            value = func(*args, **kwargs)
            store[key] = (now + max(0, int(ttl_seconds)), value)
            return value

        return wrapper

    return decorator
