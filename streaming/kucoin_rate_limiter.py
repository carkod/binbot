from threading import Lock
from time import monotonic, sleep
from typing import cast
from urllib.parse import urlsplit

from requests import PreparedRequest, Response
from kucoin_universal_sdk.model import Interceptor


class KucoinRateLimiter(Interceptor):
    """Pace streaming REST calls and slow down when KuCoin quota runs low."""

    MIN_REQUEST_INTERVAL_SECONDS = 0.2
    QUOTA_HEADROOM_RATIO = 0.2
    MIN_QUOTA_HEADROOM = 50
    VIP0_QUOTA_WINDOW_SECONDS = 30

    def __init__(self) -> None:
        self._lock = Lock()
        self._next_request_at: dict[str, float] = {}
        self._cooldown_until: dict[str, float] = {}
        self._quota: dict[str, tuple[int, int]] = {}
        self._request_weights: dict[str, int] = {}
        self._last_remaining: dict[str, int] = {}

    @staticmethod
    def _pool_key(request: PreparedRequest) -> str:
        parsed_url = urlsplit(request.url or "")
        path = parsed_url.path
        is_futures = "futures" in (parsed_url.hostname or "")

        if is_futures:
            public_prefixes = (
                "/api/v1/contracts/",
                "/api/v1/ticker",
                "/api/v1/allTickers",
                "/api/v1/level2/",
                "/api/v1/trade/history",
                "/api/v1/kline/",
                "/api/v1/mark-price/",
                "/api/v1/index/",
                "/api/v1/interest/",
                "/api/v1/premium/",
                "/api/v1/trade-statistics",
            )
            pool = "public" if path.startswith(public_prefixes) else "futures"
        else:
            public_prefixes = (
                "/api/v1/market/",
                "/api/v1/markets",
                "/api/v1/prices",
                "/api/v2/symbols",
                "/api/v3/market/",
            )
            pool = "public" if path.startswith(public_prefixes) else "spot"

        # KuCoin's public quota is shared by IP across spot and futures hosts.
        return pool

    def before(self, req: PreparedRequest) -> PreparedRequest:
        pool = self._pool_key(req)
        with self._lock:
            now = monotonic()
            scheduled_at = max(
                self._next_request_at.get(pool, now),
                self._cooldown_until.get(pool, now),
            )
            delay = max(0.0, scheduled_at - now)
            if delay:
                sleep(delay)

            now = monotonic()
            limit_and_remaining = self._quota.get(pool)
            estimated_weight = self._request_weights.get(pool, 10)
            interval = self.MIN_REQUEST_INTERVAL_SECONDS
            if limit_and_remaining is not None:
                limit, _ = limit_and_remaining
                available_weight_per_second = (
                    limit
                    * (1 - self.QUOTA_HEADROOM_RATIO)
                    / self.VIP0_QUOTA_WINDOW_SECONDS
                )
                if available_weight_per_second > 0:
                    interval = max(
                        interval, estimated_weight / available_weight_per_second
                    )
            self._next_request_at[pool] = now + interval
        return req

    def after(
        self,
        req: PreparedRequest,
        resp: Response | None,
        err: Exception | None,
    ) -> Response:
        pool = self._pool_key(req)
        now = monotonic()
        with self._lock:
            if resp is None:
                self._cooldown_until[pool] = max(
                    self._cooldown_until.get(pool, now), now + 1
                )
                return cast(Response, resp)

            try:
                limit = int(resp.headers.get("gw-ratelimit-limit", "-1"))
                remaining = int(resp.headers.get("gw-ratelimit-remaining", "-1"))
                reset_ms = int(resp.headers.get("gw-ratelimit-reset", "-1"))
            except (TypeError, ValueError):
                limit = remaining = reset_ms = -1

            if limit > 0 and remaining >= 0:
                previous_remaining = self._last_remaining.get(pool)
                if previous_remaining is not None and remaining < previous_remaining:
                    self._request_weights[pool] = max(
                        self._request_weights.get(pool, 1),
                        previous_remaining - remaining,
                    )
                self._last_remaining[pool] = remaining
                self._quota[pool] = (limit, remaining)

                headroom = max(
                    self.MIN_QUOTA_HEADROOM,
                    int(limit * self.QUOTA_HEADROOM_RATIO),
                )
                if remaining <= headroom:
                    cooldown_seconds = reset_ms / 1000 if reset_ms > 0 else 1.0
                    self._cooldown_until[pool] = max(
                        self._cooldown_until.get(pool, now),
                        now + cooldown_seconds,
                    )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                try:
                    cooldown_seconds = float(retry_after) if retry_after else 1.0
                except ValueError:
                    cooldown_seconds = 1.0
                if reset_ms > 0:
                    cooldown_seconds = max(cooldown_seconds, reset_ms / 1000)
                self._cooldown_until[pool] = max(
                    self._cooldown_until.get(pool, now), now + cooldown_seconds
                )

        return resp
