import logging
from datetime import datetime, timezone
from typing import Any, Iterable
from databases.crud.autotrade_crud import AutotradeCrud
from charts.models import AdrSeriesDb
from databases.db import Database
from databases.crud.symbols_crud import SymbolsCrud
from pymongo.errors import BulkWriteError
from pybinbot import ExchangeId, KucoinApi, BinanceApi
from tools.config import Config
from kucoin_universal_sdk.generate.spot.market.model_get_symbol_resp import (
    GetSymbolResp,
)


class MarketDominationController(Database):
    """
    CRUD operations for market domination
    """

    def __init__(self) -> None:
        super().__init__()
        self.config = Config()
        self.autotrade_db = AutotradeCrud()
        self.autotrade_settings = self.autotrade_db.get_settings()
        self.exchange = self.autotrade_settings.exchange_id
        self.symbols_crud = SymbolsCrud()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )

    def _ensure_market_breadth_collection(self) -> None:
        if "market_breadth" in self.kafka_db.list_collection_names():
            return

        self.kafka_db.create_collection(
            "market_breadth",
            timeseries={
                "timeField": "timestamp",
                "metaField": "source",
                "granularity": "hours",
            },
        )
        logging.info("Created time-series collection market_breadth")

    def migrate_adrs(self) -> int:
        self._ensure_market_breadth_collection()

        legacy_collection = self.kafka_db.advancers_decliners
        target_collection = self.kafka_db.market_breadth

        if target_collection.estimated_document_count() > 0:
            logging.info(
                "Skipping ADR migration because market_breadth already contains data"
            )
            return 0

        documents_to_insert = []
        for document in legacy_collection.find({}):
            document["source"] = document.get("source") or ExchangeId.BINANCE.value
            documents_to_insert.append(document)

        if not documents_to_insert:
            logging.info("No ADR documents needed migration into market_breadth")
            return 0

        try:
            result = target_collection.insert_many(documents_to_insert, ordered=False)
            migrated_count = len(result.inserted_ids)
        except BulkWriteError as exc:
            write_errors = exc.details.get("writeErrors", [])
            duplicate_errors = [
                error for error in write_errors if error.get("code") == 11000
            ]
            non_duplicate_errors = [
                error for error in write_errors if error.get("code") != 11000
            ]

            if non_duplicate_errors:
                raise

            migrated_count = len(
                exc.details.get("writeResult", {}).get("insertedIds", [])
            )
            if not migrated_count:
                attempted = len(documents_to_insert)
                migrated_count = max(attempted - len(duplicate_errors), 0)

        if migrated_count:
            logging.info(
                "Migrated %s ADR documents into market_breadth", migrated_count
            )
        else:
            logging.info("No ADR documents needed migration into market_breadth")

        return migrated_count

    def _get_market_breadth_tickers(self) -> tuple[Iterable[Any], datetime | None]:
        if self.exchange == ExchangeId.KUCOIN:
            response = self.kucoin_api.spot_api.get_all_tickers()
            ticker = response.common_response.data["ticker"]
            time = response.common_response.data["time"]
            timestamp = datetime.fromtimestamp(time / 1000, tz=timezone.utc)

            return ticker or [], timestamp

        ticker_data = self.binance_api.ticker_24()
        return ticker_data, None

    def _normalize_market_breadth_ticker(
        self, item: GetSymbolResp, fallback_timestamp: datetime | None = None
    ) -> dict[str, Any] | None:
        if self.exchange == ExchangeId.KUCOIN:
            close_time = fallback_timestamp
            return {
                "symbol": item["symbol"],
                "last_price": float(item.get("last", 0)),
                "price_change_percent": float(item.get("changeRate", 0)) * 100,
                "volume": float(item.get("vol", 0)),
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

    def _calculate_adr_series_data(
        self, market_tickers: Iterable[Any], fallback_timestamp: datetime | None = None
    ) -> AdrSeriesDb:
        advancers = 0
        decliners = 0
        total_volume = 0.0
        gains = []
        losses = []
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

        timestamp = timestamp or datetime.now(timezone.utc)

        return AdrSeriesDb(
            timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            advancers=advancers,
            decliners=decliners,
            total_volume=total_volume,
            strength_index=strength_index,
            avg_gain=avg_gain,
            avg_loss=avg_loss,
            source=self.exchange.value,
        )

    def ingest_adp_data(self):
        """
        Store ticker 24 data every 30 min
        and calculate ADR + Strength Index
        """
        self._ensure_market_breadth_collection()
        market_tickers, fallback_timestamp = self._get_market_breadth_tickers()
        adr_data = self._calculate_adr_series_data(market_tickers, fallback_timestamp)
        response = self.kafka_db.market_breadth.insert_one(adr_data.model_dump())
        return response

    def get_adrs(
        self, size: int = 7, window: int = 3, exchange: ExchangeId | None = None
    ) -> dict | None:
        """
        Get ADRs historical data with moving average of 'adr', using ObjectId _id for date.

        Args:
            size (int, optional): Number of data points to retrieve. Defaults to 7 (1 week).
            window (int, optional): Window size for moving average. Defaults to 3.
            exchange (ExchangeId, optional): Exchange ID to filter data. Defaults to None.
        Returns:
            list: A list of ADR data points with moving average.
        """
        self._ensure_market_breadth_collection()
        fetch_size = size + window - 1
        pipeline = [
            {"$addFields": {"timestamp_dt": "$timestamp"}},
            {"$sort": {"timestamp_dt": 1}},
            {  # Compute adp before window function
                "$addFields": {
                    "adp": {
                        "$cond": [
                            {"$ne": [{"$add": ["$advancers", "$decliners"]}, 0]},
                            {
                                "$divide": [
                                    {"$subtract": ["$advancers", "$decliners"]},
                                    {"$add": ["$advancers", "$decliners"]},
                                ]
                            },
                            None,
                        ]
                    }
                }
            },
            {
                "$setWindowFields": {
                    "sortBy": {"timestamp_dt": 1},
                    "output": {
                        "adp_ma": {
                            "$avg": "$adp",
                            "window": {"documents": [-(window - 1), 0]},
                        }
                    },
                }
            },
            {"$sort": {"timestamp_dt": -1}},
            {"$limit": fetch_size},
            {
                "$project": {
                    "_id": 0,
                    "timestamp": "$timestamp_dt",
                    "adp_ma": 1,
                    "advancers": 1,
                    "decliners": 1,
                    "strength_index": 1,
                    "total_volume": 1,
                    "adp": 1,
                }
            },
            {
                "$addFields": {
                    "timestamp": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M:%S",
                            "date": "$timestamp",
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "timestamp": {"$push": "$timestamp"},
                    "adp_ma": {"$push": "$adp_ma"},
                    "advancers": {"$push": "$advancers"},
                    "decliners": {"$push": "$decliners"},
                    "total_volume": {"$push": "$total_volume"},
                    "adp": {"$push": "$adp"},
                    "strength_index": {"$push": "$strength_index"},
                }
            },
            {"$project": {"_id": 0}},
        ]
        if exchange:
            pipeline.insert(0, {"$match": {"source": exchange.value}})
        results = self.kafka_db.market_breadth.aggregate(pipeline)
        data = list(results)
        if len(data) > 0:
            return data[0]
        return None

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
