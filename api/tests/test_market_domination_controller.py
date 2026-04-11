from datetime import datetime
from types import SimpleNamespace

from charts.controllers import MarketDominationController
from databases.tables.autotrade_table import AutotradeTable
from pybinbot import ExchangeId


class CollectionStub:
    def __init__(self):
        self.inserted_docs = []

    def insert_one(self, doc):
        self.inserted_docs.append(doc)
        return doc


def _make_controller(exchange_id: ExchangeId, fiat: str = "USDC"):
    controller = MarketDominationController.__new__(MarketDominationController)
    controller.exchange = exchange_id
    controller.autotrade_settings = AutotradeTable(fiat=fiat, exchange_id=exchange_id)
    controller.kafka_db = SimpleNamespace(
        list_collection_names=lambda: ["market_breadth"],
        market_breadth=CollectionStub(),
    )
    return controller


def test_migrate_adrs_copies_legacy_documents_to_market_breadth():
    legacy_docs = [
        {
            "_id": "legacy-binance",
            "timestamp": datetime(2025, 9, 14, 0, 5, 13),
            "advancers": 187,
            "decliners": 57,
            "total_volume": 6912803774816.687,
            "strength_index": 0.5924651628279104,
        },
        {
            "_id": "legacy-kucoin",
            "timestamp": datetime(2026, 4, 11, 5, 27, 0),
            "advancers": 443,
            "decliners": 445,
            "total_volume": 82548895987280.3,
            "strength_index": 0.20350799552462534,
            "source": ExchangeId.KUCOIN.value,
        },
    ]

    inserted_docs: list[dict] = []

    class MarketBreadthStub(CollectionStub):
        def count_documents(self, query, limit=0):
            return int(any(doc["_id"] == query["_id"] for doc in inserted_docs))

        def insert_one(self, doc):
            inserted_docs.append(doc)
            return doc

    controller = _make_controller(ExchangeId.BINANCE)
    controller.kafka_db = SimpleNamespace(
        list_collection_names=lambda: [],
        create_collection=lambda *args, **kwargs: None,
        advancers_decliners=SimpleNamespace(find=lambda query=None: legacy_docs),
        market_breadth=MarketBreadthStub(),
    )

    migrated_count = controller.migrate_adrs()

    assert migrated_count == 2
    assert inserted_docs[0]["source"] == ExchangeId.BINANCE.value
    assert inserted_docs[1]["source"] == ExchangeId.KUCOIN.value


def test_ingest_adp_data_uses_binance_ticker_payload():
    controller = _make_controller(ExchangeId.BINANCE)
    controller.binance_api = SimpleNamespace(
        ticker_24=lambda: [
            {
                "symbol": "BTCUSDC",
                "lastPrice": "100",
                "priceChangePercent": "10",
                "volume": "5",
                "closeTime": 1710000000000,
            },
            {
                "symbol": "ETHUSDC",
                "lastPrice": "200",
                "priceChangePercent": "-5",
                "volume": "2",
                "closeTime": 1710000000000,
            },
            {
                "symbol": "XRPBTC",
                "lastPrice": "1",
                "priceChangePercent": "25",
                "volume": "99",
                "closeTime": 1710000000000,
            },
        ]
    )

    inserted = controller.ingest_adp_data()

    assert controller.kafka_db.market_breadth.inserted_docs[0] == inserted
    assert inserted["advancers"] == 1
    assert inserted["decliners"] == 1
    assert inserted["total_volume"] == 7.0
    assert inserted["strength_index"] == 1 / 3
    assert inserted["source"] == ExchangeId.BINANCE.value
    assert inserted["timestamp"] == datetime.fromtimestamp(1710000000000 / 1000)


def test_ingest_adp_data_uses_kucoin_all_tickers_payload():
    controller = _make_controller(ExchangeId.KUCOIN)
    controller.kucoin_api = SimpleNamespace(
        spot_api=SimpleNamespace(
            get_all_tickers=lambda: SimpleNamespace(
                common_response=SimpleNamespace(
                    data={
                        "time": 1710000000000,
                        "ticker": [
                            {
                                "symbol": "BTC-USDC",
                                "last": "100",
                                "changeRate": "0.1",
                                "vol": "500",
                            },
                            {
                                "symbol": "ETH-USDC",
                                "last": "200",
                                "changeRate": "-0.05",
                                "vol": "200",
                            },
                            {
                                "symbol": "XRP-BTC",
                                "last": "1",
                                "changeRate": "0.25",
                                "vol": "999",
                            },
                        ],
                    }
                )
            )
        )
    )

    inserted = controller.ingest_adp_data()

    assert controller.kafka_db.market_breadth.inserted_docs[0] == inserted
    assert inserted["advancers"] == 1
    assert inserted["decliners"] == 1
    assert inserted["total_volume"] == 700.0
    assert inserted["strength_index"] == 1 / 3
    assert inserted["source"] == ExchangeId.KUCOIN.value
    assert inserted["timestamp"] == datetime.fromtimestamp(1710000000000 / 1000)
