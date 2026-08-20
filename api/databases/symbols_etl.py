from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from time import time

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlmodel import col, select

from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable
from api.databases.utils import get_db_session
from pybinbot import (
    BinbotErrors,
    ExchangeId,
    FuturesContractMarketData,
    QuoteAssets,
    timestamp,
)
from kucoin_universal_sdk.generate.spot.market.model_get_all_symbols_resp import (
    GetAllSymbolsResp,
)
from kucoin_universal_sdk.generate.futures.market.model_get_all_symbols_resp import (
    GetAllSymbolsResp as FuturesGetAllSymbolsResp,
)

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS
ASSET_CLASS_LOOKBACK_DAYS = 90
ASSET_CLASS_HISTORY_DAYS = 60
ASSET_CLASS_MIN_WINDOWS = 30
ASSET_CLASS_MIN_UNIVERSE_SIZE = 40
ASSET_CLASS_MIN_FETCH_COVERAGE = 0.80
ASSET_CLASS_FETCH_WORKERS = 5
NON_CRYPTO_REFERENCE_SYMBOLS = {
    "ANTHROPICUSDTM",
    "COPPERUSDTM",
    "NATGASUSDTM",
    "OPENAIUSDTM",
    "PAXGUSDTM",
    "XAGUSDTM",
    "XAUTUSDTM",
}


def _is_crypto_contract(
    contract: FuturesContractMarketData,
    production_symbol_ids: set[str],
) -> bool:
    symbol = contract.symbol
    is_tradfi_reference = any(
        source == "finnhub" or source.endswith("_index")
        for source in contract.source_exchanges
    )
    return bool(
        symbol
        and symbol in production_symbol_ids
        and contract.status == "Open"
        and contract.quote_currency == "USDT"
        and symbol not in NON_CRYPTO_REFERENCE_SYMBOLS
        and not is_tradfi_reference
        and (contract.turnover_24h or 0) > 0
    )


def _prepare_asset_class_frame(rows: list[list[float]]) -> pd.DataFrame:
    normalized_rows = [row[:7] for row in rows if len(row) >= 7]
    frame = pd.DataFrame(
        normalized_rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ],
    )
    if frame.empty:
        return frame

    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame.dropna(subset=["timestamp", "high", "low", "close"])
        .loc[lambda data: data.close > 0]
        .drop_duplicates("timestamp")
        .sort_values("timestamp")
    )

    previous_close = frame.close.shift(1)
    true_range = pd.concat(
        [
            frame.high - frame.low,
            (frame.high - previous_close).abs(),
            (frame.low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    up = frame.high.diff()
    down = -frame.low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    minus_di = (
        100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    )
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    frame["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rolling_range = frame.high.rolling(14).max() - frame.low.rolling(14).min()
    frame["chop"] = (
        100
        * np.log10(true_range.rolling(14).sum() / rolling_range.replace(0, np.nan))
        / np.log10(14)
    )
    return frame


def _efficiency(log_close: np.ndarray) -> float:
    path = np.abs(np.diff(log_close)).sum()
    return float(abs(log_close[-1] - log_close[0]) / path) if path else 0.0


def _trend_fit(window: pd.DataFrame) -> tuple[float, float]:
    log_close = np.log(window.close.to_numpy())
    hours = (window.timestamp.to_numpy() - window.timestamp.iloc[0]) / HOUR_MS
    slope, intercept = np.polyfit(hours, log_close, 1)
    predicted = slope * hours + intercept
    total = ((log_close - log_close.mean()) ** 2).sum()
    residual = ((log_close - predicted) ** 2).sum()
    return float(slope), float(1 - residual / total if total else 0.0)


def _variance_ratio(log_close: np.ndarray, lag: int = 24) -> float:
    one_period = np.diff(log_close)
    multi_period = log_close[lag:] - log_close[:-lag]
    if len(one_period) < lag * 3 or np.var(one_period, ddof=1) == 0:
        return float("nan")
    return float(np.var(multi_period, ddof=1) / (lag * np.var(one_period, ddof=1)))


def _persistent_asset_class(
    history: list[tuple[int, str, str]],
) -> str:
    if len(history) < ASSET_CLASS_MIN_WINDOWS:
        return ""

    current_regime = history[-1][1]
    current_direction = history[-1][2]
    counts = Counter(item[1] for item in history)
    dominant_regime, dominant_count = counts.most_common(1)[0]
    current_share = counts[current_regime] / len(history)

    current_streak = 0
    for _, regime, _ in reversed(history):
        if regime != current_regime:
            break
        current_streak += 1

    if (
        current_regime == "mixed/choppy"
        or current_regime != dominant_regime
        or dominant_count / len(history) < 0.50
        or current_share < 0.50
        or current_streak < 3
    ):
        return ""

    if current_regime == "range":
        return "persistent_range"

    trend_directions = [
        direction for _, regime, direction in history if regime == "trend"
    ]
    direction_share = trend_directions.count(current_direction) / len(trend_directions)
    if direction_share < 0.65:
        return ""
    return f"persistent_{current_direction}trend"


def _classify_persistent_regimes(
    candles_by_symbol: dict[str, list[list[float]]],
    end_ms: int,
) -> tuple[dict[str, str], set[str]]:
    frames = {
        symbol: frame
        for symbol, rows in candles_by_symbol.items()
        if not (frame := _prepare_asset_class_frame(rows)).empty
    }
    snapshots: dict[int, pd.DataFrame] = {}

    for endpoint in [
        end_ms - offset * DAY_MS for offset in range(ASSET_CLASS_HISTORY_DAYS, -1, -1)
    ]:
        feature_rows: list[dict[str, str | float]] = []
        for symbol, frame in frames.items():
            month = frame[
                (frame.timestamp > endpoint - 30 * DAY_MS)
                & (frame.timestamp <= endpoint)
            ]
            week = month[month.timestamp > endpoint - 7 * DAY_MS]
            if (
                len(month) < 500
                or len(week) < 100
                or month.timestamp.iloc[0] > endpoint - 28 * DAY_MS
                or week.timestamp.iloc[0] > endpoint - 6 * DAY_MS
            ):
                continue

            log_week = np.log(week.close.to_numpy())
            log_month = np.log(month.close.to_numpy())
            slope, trend_r_squared = _trend_fit(week)
            feature_rows.append(
                {
                    "symbol": symbol,
                    "efficiency": _efficiency(log_week),
                    "adx": float(week.adx.median()),
                    "trend_r_squared": max(0.0, min(1.0, trend_r_squared)),
                    "variance_ratio": _variance_ratio(log_month),
                    "choppiness": float(week.chop.median()),
                    "slope": slope,
                }
            )

        if len(feature_rows) < ASSET_CLASS_MIN_UNIVERSE_SIZE:
            continue

        features = pd.DataFrame(feature_rows).set_index("symbol")

        def rank(column: str, ascending: bool = True) -> pd.Series:
            return features[column].rank(pct=True, ascending=ascending).fillna(0.5)

        features["trend_score"] = (
            0.30 * rank("efficiency")
            + 0.25 * rank("adx")
            + 0.20 * rank("trend_r_squared")
            + 0.15 * rank("variance_ratio")
            + 0.10 * rank("choppiness", False)
        )
        features["range_score"] = (
            0.25 * rank("efficiency", False)
            + 0.20 * rank("adx", False)
            + 0.20 * rank("choppiness")
            + 0.20
            * (features.variance_ratio - 1)
            .abs()
            .rank(pct=True, ascending=False)
            .fillna(0.5)
            + 0.15 * rank("trend_r_squared", False)
        )
        features["regime"] = "mixed/choppy"
        features.loc[
            (features.trend_score >= 0.62)
            & (features.trend_score - features.range_score >= 0.08),
            "regime",
        ] = "trend"
        features.loc[
            (features.range_score >= 0.62)
            & (features.range_score - features.trend_score >= 0.08),
            "regime",
        ] = "range"
        features["direction"] = np.where(features.slope >= 0, "up", "down")
        snapshots[endpoint] = features

    if not snapshots:
        return {}, set()

    latest_endpoint = max(snapshots)
    latest = snapshots[latest_endpoint]
    classifications: dict[str, str] = {}
    for symbol in latest.index:
        history = [
            (
                endpoint,
                str(snapshot.loc[symbol, "regime"]),
                str(snapshot.loc[symbol, "direction"]),
            )
            for endpoint, snapshot in snapshots.items()
            if symbol in snapshot.index
        ]
        asset_class = _persistent_asset_class(history)
        if asset_class:
            classifications[str(symbol)] = asset_class

    return classifications, {str(symbol) for symbol in latest.index}


class SymbolDataEtl(SymbolsCrud):
    """
    Exchange data manipulation to ingest symbols
    data into the database before CRUD operations.
    """

    def __init__(self):
        super().__init__()
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.fiat = self.autotrade_settings.fiat

    def binance_symbols_reingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        for item in exchange_info_data["symbols"]:
            if item["status"] != "TRADING":
                continue
            if item["quoteAsset"] == "TRY":
                continue

            try:
                self.get_symbol(item["symbol"])
            except BinbotErrors:
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def binance_symbols_ingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        filtered_symbols = [
            item
            for item in exchange_info_data["symbols"]
            if str(item["symbol"]).endswith(self.fiat)
        ]

        for item in filtered_symbols:
            if item["status"] != "TRADING" or item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue
            if item["quoteAsset"] == "TRY":
                continue
            if item["quoteAsset"] in list(QuoteAssets):
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def ingest_futures_data(self, all_raw_symbols: FuturesGetAllSymbolsResp):
        """
        - Ingest futures data as a data seed (empty local database)
        - Reingests through cronjob
        - Resets data (when delete_existing=True)
        """
        for item in all_raw_symbols.data:
            symbol = item.symbol

            futures_suffix = f"{self.fiat}M" if self.fiat == "USDT" else self.fiat
            if futures_suffix and not symbol.endswith(futures_suffix):
                continue

            active = True
            if symbol.startswith(("BTC", "ETH")):
                active = False

            if item.quote_currency in list(QuoteAssets):
                price_precision = self._convert_to_int(item.tick_size)
                qty_precision = self._convert_to_int(item.lot_size)
                multiplier = float(item.multiplier)
                min_notional = self._convert_to_int(
                    float(item.tick_size) * float(item.lot_size) * multiplier
                )

                with get_db_session() as s:
                    result = s.exec(
                        select(SymbolTable).where(SymbolTable.id == symbol)
                    ).first()
                    if result:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=False,
                            multiplier=multiplier,
                        )
                    else:
                        self.add_symbol(
                            symbol=symbol,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            exchange_id=ExchangeId.KUCOIN,
                            active=active,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            min_notional=min_notional,
                            multiplier=multiplier,
                        )
                        # ensure exchange link added in same session
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=False,
                            multiplier=multiplier,
                        )

    def ingest_spot_data(self, all_raw_symbols: GetAllSymbolsResp):
        for item in all_raw_symbols.data:
            symbol = item.symbol.replace("-", "")
            price_precision = self._convert_to_int(item.price_increment)
            qty_precision = self._convert_to_int(item.base_increment)
            min_notional = float(item.min_funds or item.quote_min_size or 0)

            if not symbol.endswith(self.fiat):
                continue

            if not item.enable_trading or item.symbol.startswith(
                ("DOWN", "UP", "AUD", "EUR", "GBP")
            ):
                continue

            if item.st:
                # assets to be delisted
                try:
                    with get_db_session() as s:
                        result = s.exec(
                            select(SymbolTable).where(SymbolTable.id == symbol)
                        ).first()
                        if result:
                            result.active = False
                            result.blacklist_reason = "At risk to be delisted soon"
                            s.add(result)
                            s.flush()
                            s.refresh(result)
                            self._add_exchange_link_if_not_exists(
                                s,
                                symbol=symbol,
                                exchange_id=ExchangeId.KUCOIN,
                                min_notional=min_notional,
                                price_precision=price_precision,
                                qty_precision=qty_precision,
                                quote_asset=item.quote_currency,
                                base_asset=item.base_currency,
                                is_margin_trading_allowed=item.is_margin_enabled,
                            )
                    continue
                except Exception as e:
                    logging.error(f"Error updating delisted symbol {symbol}: {e}")
                    continue

            active = True
            if symbol in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                active = False

            if item.quote_currency in list(QuoteAssets):
                with get_db_session() as s:
                    result = s.exec(
                        select(SymbolTable).where(SymbolTable.id == symbol)
                    ).first()
                    if result:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )
                    else:
                        self.add_symbol(
                            symbol=symbol,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            exchange_id=ExchangeId.KUCOIN,
                            active=active,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            min_notional=min_notional,
                        )
                        # ensure exchange link added in same session
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )

    def kucoin_symbols_ingestion(self):
        all_spot_symbols = self.kucoin_api.get_all_symbols()
        all_future_symbols = (
            self.kucoin_futures_api.futures_market_api.get_all_symbols()
        )

        self.ingest_spot_data(all_spot_symbols)
        self.ingest_futures_data(all_future_symbols)

    def classify_persistent_crypto_assets(
        self,
    ) -> tuple[dict[str, str], set[str], set[str]]:
        """Classify persistent regimes across the active production crypto universe."""
        with get_db_session() as session:
            production_symbol_ids = set(
                session.exec(
                    select(SymbolTable.id)
                    .join(SymbolExchangeTable)
                    .where(
                        col(SymbolTable.active).is_(True),
                        SymbolExchangeTable.exchange_id == ExchangeId.KUCOIN,
                    )
                ).all()
            )

        if not production_symbol_ids:
            return {}, set(), set()

        contracts = self.kucoin_futures_api.get_active_contracts()
        active_crypto_symbols = {
            contract.symbol
            for contract in contracts
            if _is_crypto_contract(contract, production_symbol_ids)
        }
        if not active_crypto_symbols:
            return {}, set(), set()

        end_ms = int(time() * 1000)
        end_ms -= end_ms % HOUR_MS
        candles_by_symbol: dict[str, list[list[float]]] = {}
        fetch_errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=ASSET_CLASS_FETCH_WORKERS) as executor:
            futures = {
                executor.submit(
                    self.kucoin_futures_api.get_historical_klines,
                    symbol=symbol,
                    interval="1hour",
                    start_time=end_ms - ASSET_CLASS_LOOKBACK_DAYS * DAY_MS,
                    end_time=end_ms,
                ): symbol
                for symbol in active_crypto_symbols
            }
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    candles_by_symbol[symbol] = future.result()
                except Exception as exc:
                    fetch_errors[symbol] = f"{type(exc).__name__}: {exc}"

        fetch_coverage = len(candles_by_symbol) / len(active_crypto_symbols)
        if (
            len(candles_by_symbol) < ASSET_CLASS_MIN_UNIVERSE_SIZE
            or fetch_coverage < ASSET_CLASS_MIN_FETCH_COVERAGE
        ):
            raise RuntimeError(
                "Persistent asset classification aborted: fetched "
                f"{len(candles_by_symbol)}/{len(active_crypto_symbols)} "
                f"crypto contracts ({fetch_coverage:.1%})"
            )

        if fetch_errors:
            logging.warning(
                "Persistent asset classification skipped %d/%d contracts with "
                "candle errors: %s",
                len(fetch_errors),
                len(active_crypto_symbols),
                ", ".join(sorted(fetch_errors)),
            )

        classifications, evaluated_symbols = _classify_persistent_regimes(
            candles_by_symbol,
            end_ms,
        )
        if len(evaluated_symbols) < ASSET_CLASS_MIN_UNIVERSE_SIZE:
            raise RuntimeError(
                "Persistent asset classification aborted: only "
                f"{len(evaluated_symbols)} contracts had complete current coverage"
            )
        return classifications, evaluated_symbols, active_crypto_symbols

    def update_asset_classes(self) -> dict[str, str]:
        """Recompute and persist only full-universe persistent crypto regimes."""
        classifications, evaluated_symbols, active_crypto_symbols = (
            self.classify_persistent_crypto_assets()
        )
        if not active_crypto_symbols:
            logging.info("No active production crypto contracts to classify.")
            return {}

        updated_count = 0
        with get_db_session() as session:
            symbols = session.exec(select(SymbolTable)).all()
            for symbol in symbols:
                if symbol.id in evaluated_symbols:
                    new_asset_class = classifications.get(symbol.id, "")
                elif symbol.id not in active_crypto_symbols:
                    new_asset_class = ""
                else:
                    # Preserve the last good value when this week's candle fetch failed.
                    continue

                if symbol.asset_class == new_asset_class:
                    continue
                symbol.asset_class = new_asset_class
                symbol.updated_at = timestamp()
                session.add(symbol)
                updated_count += 1

        logging.info(
            "Persistent asset classification stored %d classes after evaluating %d "
            "contracts (%d rows changed).",
            len(classifications),
            len(evaluated_symbols),
            updated_count,
        )
        return classifications

    def etl_symbols_ingestion(
        self,
        delete_existing: bool = False,
        update_asset_classes: bool = True,
    ):
        if delete_existing:
            # TRUNCATE in its own fresh session so it never conflicts with earlier SELECTs
            with get_db_session() as s:
                s.execute(text("TRUNCATE TABLE symbol CASCADE"))

        exchange_id = self.autotrade_settings.exchange_id

        if exchange_id == ExchangeId.BINANCE:
            self.binance_symbols_ingestion()
            logging.info("Binance symbols ingestion completed.")
        elif exchange_id == ExchangeId.KUCOIN:
            self.kucoin_symbols_ingestion()
            logging.info("Kucoin symbols ingestion completed.")
            if update_asset_classes:
                self.update_asset_classes()
        else:
            logging.warning(
                "Skipping symbols ingestion for unsupported exchange %s",
                exchange_id,
            )
