import logging
from datetime import datetime, timezone
from typing import Any, Iterable, cast
from sqlalchemy import Table
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from api.charts.models import MarketBreadthSample, MarketBreadthSeries
from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.market_breadth_table import MarketBreadthTable
from api.databases.utils import independent_session
from kucoin_universal_sdk.generate.spot.market.model_get_symbol_resp import (
    GetSymbolResp,
)
from pybinbot import BinanceApi, ExchangeId, KucoinApi
from api.tools.config import Config
from api.tools.utils import datetime_to_iso, utc_now


class MarketDominationController:
    """
    Reads/writes market-breadth samples in Postgres.
    """

    def __init__(self, session: Session | None = None) -> None:
        self.config = Config()
        self.session = session if session is not None else independent_session()
        self.autotrade_db = AutotradeCrud(session=self.session)
        self.autotrade_settings = self.autotrade_db.get_settings()
        self.exchange = ExchangeId(self.autotrade_settings.exchange_id)
        self.symbols_crud = SymbolsCrud()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )

    def _normalize_market_breadth_ticker(
        self, item: GetSymbolResp, fallback_timestamp: datetime | None = None
    ) -> dict[str, Any] | None:
        if self.exchange == ExchangeId.KUCOIN:
            close_time = fallback_timestamp
            if item["last"] is None:
                # auction coin
                return None
            return {
                "symbol": item["symbol"],
                "last_price": float(item["last"]),
                "price_change_percent": float(item.get("changeRate", 0)) * 100,
                "volume": float(item["vol"]),
                "close_time": close_time,
            }

        return {
            "symbol": item["symbol"],
            "last_price": float(item["lastPrice"]),
            "price_change_percent": float(item["priceChangePercent"]),
            "volume": float(item["volume"]),
            "close_time": datetime.fromtimestamp(
                float(item["closeTime"]) / 1000, tz=timezone.utc
            ),
        }

    def _calculate_market_breadth_sample(
        self, market_tickers: Iterable[Any], fallback_timestamp: datetime | None = None
    ) -> MarketBreadthSample:
        advancers = 0
        decliners = 0
        total_volume = 0.0
        gains: list[float] = []
        losses: list[float] = []
        timestamp = fallback_timestamp

        for raw_item in market_tickers:
            item = self._normalize_market_breadth_ticker(raw_item, fallback_timestamp)
            if not item:
                continue

            if (
                item["symbol"].endswith(self.autotrade_settings.fiat)
                and float(item["last_price"]) > 0
            ):
                price_change_percent = item["price_change_percent"]

                if price_change_percent > 0:
                    advancers += 1
                    gains.append(price_change_percent)
                elif price_change_percent < 0:
                    decliners += 1
                    losses.append(price_change_percent)

                total_volume += item["volume"]
                timestamp = item["close_time"]

        avg_gain = sum(gains) / len(gains) if gains else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

        gain_power = advancers * avg_gain
        loss_power = decliners * avg_loss

        if (gain_power + loss_power) > 0:
            strength_index = (gain_power - loss_power) / (gain_power + loss_power)
        else:
            strength_index = 0.0

        if (advancers + decliners) > 0:
            market_breadth = (advancers - decliners) / (advancers + decliners)
        else:
            market_breadth = 0.0

        timestamp = timestamp or utc_now()

        return MarketBreadthSample(
            timestamp=timestamp,
            source=self.exchange.value,
            advancers=advancers,
            decliners=decliners,
            market_breadth=market_breadth,
            avg_gain=avg_gain,
            avg_loss=avg_loss,
            total_volume=total_volume,
            strength_index=strength_index,
        )

    def ingest_market_breadth(self) -> dict[str, Any] | None:
        """
        Capture one market-breadth sample. Called every 15 min by the cron.
        """
        if self.exchange == ExchangeId.KUCOIN:
            response = self.kucoin_api.spot_api.get_all_tickers()
            ticker = response.common_response.data["ticker"]
            time_ms = response.common_response.data["time"]
            fallback_timestamp = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
            market_tickers = ticker or []
        else:
            ticker_data = self.binance_api.ticker_24()
            market_tickers = ticker_data or []
            fallback_timestamp = None

        market_breadth_sample = self._calculate_market_breadth_sample(
            market_tickers, fallback_timestamp
        )
        payload = market_breadth_sample.model_dump()

        row = MarketBreadthTable(
            timestamp=market_breadth_sample.timestamp,
            source=market_breadth_sample.source,
            advancers=market_breadth_sample.advancers,
            decliners=market_breadth_sample.decliners,
            adp=market_breadth_sample.market_breadth,
            avg_gain=market_breadth_sample.avg_gain,
            avg_loss=market_breadth_sample.avg_loss,
            total_volume=market_breadth_sample.total_volume,
            strength_index=market_breadth_sample.strength_index,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError as exc:
            # (timestamp, source) already exists — duplicate cron tick.
            self.session.rollback()
            logging.warning(
                "market_breadth integrity error for ts=%s src=%s: %s",
                market_breadth_sample.timestamp,
                market_breadth_sample.source,
                exc,
            )
            return None
        return payload

    @staticmethod
    def _ema(values: list[float], window: int) -> list[float]:
        alpha = 2 / (max(int(window), 1) + 1)
        smoothed: list[float] = []
        current: float | None = None

        for value in values:
            current = (
                value if current is None else alpha * value + (1 - alpha) * current
            )
            smoothed.append(current)

        return smoothed

    def get_market_breadth_series(
        self, size: int = 7, window: int = 8, exchange: ExchangeId | None = None
    ) -> dict[str, list] | None:
        """
        Return parallel arrays (newest-first). Every field is read straight from
        storage except market_breadth_ma, which is an EMA-smoothed market
        breadth level computed over chronological samples.
        """
        output_size = size + max(int(window) - 1, 0)
        fetch_size = output_size + max(int(window) * 3, 0)
        market_breadth = cast(Table, getattr(MarketBreadthTable, "__table__"))

        recent_columns = (
            market_breadth.c.timestamp,
            market_breadth.c.advancers,
            market_breadth.c.decliners,
            market_breadth.c.total_volume,
            market_breadth.c.strength_index,
            market_breadth.c.adp.label("market_breadth"),
            market_breadth.c.avg_gain,
            market_breadth.c.avg_loss,
        )

        recent_stmt = market_breadth.select().with_only_columns(*recent_columns)
        if exchange:
            recent_stmt = recent_stmt.where(market_breadth.c.source == exchange.value)

        stmt = recent_stmt.order_by(market_breadth.c.timestamp.desc()).limit(fetch_size)
        result = self.session.execute(stmt)
        rows = result.mappings().all()

        if not rows:
            return None

        chronological_rows = list(reversed(rows))
        chronological_market_breadth = [
            float(r["market_breadth"]) for r in chronological_rows
        ]
        chronological_ema = self._ema(chronological_market_breadth, window)
        rows_with_ema = list(zip(chronological_rows, chronological_ema, strict=True))
        output_rows = list(reversed(rows_with_ema))[:output_size]

        return MarketBreadthSeries(
            timestamp=[datetime_to_iso(r["timestamp"]) for r, _ in output_rows],
            advancers=[r["advancers"] for r, _ in output_rows],
            decliners=[r["decliners"] for r, _ in output_rows],
            market_breadth=[float(r["market_breadth"]) for r, _ in output_rows],
            market_breadth_ma=[float(ema) for _, ema in output_rows],
            avg_gain=[float(r["avg_gain"]) for r, _ in output_rows],
            avg_loss=[float(r["avg_loss"]) for r, _ in output_rows],
            total_volume=[float(r["total_volume"]) for r, _ in output_rows],
            strength_index=[float(r["strength_index"]) for r, _ in output_rows],
        ).model_dump()

    def gainers_losers(self) -> tuple[Iterable[Any], Iterable[Any]]:
        """
        Get market top gainers of the day

        ATTENTION - This is a very heavy weight operation
        ticker_24() retrieves all tokens
        """
        fiat = self.autotrade_db.get_fiat()
        ticker_data = self.binance_api.ticker_24()

        gainers = sorted(
            [
                item
                for item in ticker_data
                if float(item["priceChangePercent"]) > 0
                and item["symbol"].endswith(fiat)
            ],
            key=lambda x: float(x["priceChangePercent"]),
            reverse=True,
        )

        losers = sorted(
            [
                item
                for item in ticker_data
                if float(item["priceChangePercent"]) < 0
                and item["symbol"].endswith(fiat)
            ],
            key=lambda x: float(x["priceChangePercent"]),
        )

        return gainers[:10], losers[:10]
