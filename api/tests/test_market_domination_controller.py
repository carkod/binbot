from datetime import datetime
from types import SimpleNamespace

from charts.controllers import MarketDominationController
from databases.tables.autotrade_table import AutotradeTable
from pybinbot import ExchangeId


def _make_controller(exchange_id: ExchangeId, fiat: str = "USDC"):
    controller = MarketDominationController.__new__(MarketDominationController)
    controller.exchange = exchange_id
    controller.autotrade_settings = AutotradeTable(fiat=fiat, exchange_id=exchange_id)
    controller.kafka_db = SimpleNamespace(
        advancers_decliners=SimpleNamespace(insert_one=lambda doc: doc)
    )
    return controller


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

    assert inserted["advancers"] == 1
    assert inserted["decliners"] == 1
    assert inserted["total_volume"] == 700.0
    assert inserted["strength_index"] == 1 / 3
    assert inserted["source"] == ExchangeId.KUCOIN.value
    assert inserted["timestamp"] == datetime.fromtimestamp(1710000000000 / 1000)
