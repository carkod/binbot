from time import time_ns

import pytest
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq

from api.exchange_apis.kucoin.futures.liquidity import (
    FuturesOrderBook,
    OrderBookLevel,
    calculate_liquidity_snapshot,
    load_futures_order_book,
)


def representative_order_book() -> FuturesOrderBook:
    now_ms = time_ns() // 1_000_000
    return FuturesOrderBook(
        symbol="TESTUSDTM",
        bids=(
            OrderBookLevel(price=99.9, contracts=5),
            OrderBookLevel(price=99.8, contracts=10),
            OrderBookLevel(price=99.5, contracts=20),
        ),
        asks=(
            OrderBookLevel(price=100.1, contracts=2),
            OrderBookLevel(price=100.2, contracts=3),
            OrderBookLevel(price=100.5, contracts=10),
        ),
        exchange_timestamp_ms=now_ms - 125,
        received_timestamp_ms=now_ms,
    )


def test_buy_liquidity_snapshot_reports_depth_vwap_slippage_and_imbalance():
    snapshot = calculate_liquidity_snapshot(
        representative_order_book(),
        AddOrderReq.SideEnum.BUY,
        requested_contracts=4,
        permitted_price_band_bps=25,
    )

    assert snapshot.spread_bps == pytest.approx(20)
    assert snapshot.bid_depth_10_bps == 5
    assert snapshot.ask_depth_10_bps == 2
    assert snapshot.bid_depth_25_bps == 15
    assert snapshot.ask_depth_25_bps == 5
    assert snapshot.bid_depth_50_bps == 35
    assert snapshot.ask_depth_50_bps == 15
    assert snapshot.contracts_fillable == 5
    assert snapshot.expected_average_fill_price == pytest.approx(100.15)
    assert snapshot.expected_slippage_bps == pytest.approx(15)
    assert snapshot.worst_fill_price == 100.2
    assert snapshot.book_imbalance == pytest.approx(0.4)
    assert snapshot.data_age_ms == 125


def test_sell_liquidity_snapshot_walks_bid_levels_for_requested_size():
    snapshot = calculate_liquidity_snapshot(
        representative_order_book(),
        AddOrderReq.SideEnum.SELL,
        requested_contracts=8,
        permitted_price_band_bps=25,
    )

    assert snapshot.contracts_fillable == 15
    assert snapshot.expected_average_fill_price == pytest.approx(99.8625)
    assert snapshot.expected_slippage_bps == pytest.approx(13.75)
    assert snapshot.worst_fill_price == 99.8


def test_order_book_loader_normalizes_raw_levels_and_nanosecond_age():
    exchange_timestamp_ns = time_ns() - 500_000_000

    class FuturesMarketApi:
        def get_full_order_book(self, request):
            return type(
                "Book",
                (),
                {
                    "bids": [["99.8", "2"], ["99.9", "1"]],
                    "asks": [["100.2", "4"], ["100.1", "3"]],
                    "ts": exchange_timestamp_ns,
                },
            )()

    api = type("Api", (), {"futures_market_api": FuturesMarketApi()})()

    order_book = load_futures_order_book(api, "TESTUSDTM")

    assert [level.price for level in order_book.bids] == [99.9, 99.8]
    assert [level.price for level in order_book.asks] == [100.1, 100.2]
    assert 450 <= order_book.data_age_ms <= 1_000
