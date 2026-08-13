from time import time_ns
from typing import Any

from kucoin_universal_sdk.generate.futures.market import GetPartOrderBookReqBuilder
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq

from api.exchange_apis.kucoin.futures.models import (
    FuturesOrderBook,
    LiquiditySnapshot,
    OrderBookLevel,
)


ORDER_BOOK_DEPTH_LEVELS = 100
DEPTH_BANDS_BPS = (10, 25, 50)


def _exchange_timestamp_ms(raw_timestamp: Any) -> int:
    try:
        timestamp_value = float(raw_timestamp)
    except (TypeError, ValueError) as error:
        raise ValueError("KuCoin order book timestamp is missing or invalid") from error

    if timestamp_value <= 0:
        raise ValueError("KuCoin order book timestamp must be positive")

    if timestamp_value >= 1e17:
        return int(timestamp_value / 1_000_000)
    if timestamp_value >= 1e14:
        return int(timestamp_value / 1_000)
    if timestamp_value >= 1e11:
        return int(timestamp_value)
    return int(timestamp_value * 1_000)


def _levels(raw_levels: Any, *, descending: bool) -> tuple[OrderBookLevel, ...]:
    levels: list[OrderBookLevel] = []
    for raw_level in raw_levels or []:
        if not isinstance(raw_level, (list, tuple)) or len(raw_level) < 2:
            continue
        try:
            price = float(raw_level[0])
            contracts = float(raw_level[1])
        except (TypeError, ValueError):
            continue
        if price <= 0 or contracts <= 0:
            continue
        levels.append(OrderBookLevel(price=price, contracts=contracts))

    return tuple(sorted(levels, key=lambda level: level.price, reverse=descending))


def load_futures_order_book(futures_api: Any, symbol: str) -> FuturesOrderBook:
    """Load and normalize one current KuCoin futures L2 snapshot."""
    request = (
        GetPartOrderBookReqBuilder()
        .set_size(str(ORDER_BOOK_DEPTH_LEVELS))
        .set_symbol(symbol)
        .build()
    )
    response = futures_api.futures_market_api.get_full_order_book(request)
    received_timestamp_ms = time_ns() // 1_000_000

    bids = _levels(getattr(response, "bids", None), descending=True)
    asks = _levels(getattr(response, "asks", None), descending=False)
    if not bids or not asks:
        raise ValueError(f"KuCoin order book for {symbol} has no usable bids or asks")
    if bids[0].price >= asks[0].price:
        raise ValueError(
            f"KuCoin order book for {symbol} is crossed: "
            f"bid={bids[0].price}, ask={asks[0].price}"
        )

    return FuturesOrderBook(
        symbol=symbol,
        bids=bids,
        asks=asks,
        exchange_timestamp_ms=_exchange_timestamp_ms(getattr(response, "ts", None)),
        received_timestamp_ms=received_timestamp_ms,
    )


def _depth_within_bps(
    levels: tuple[OrderBookLevel, ...],
    midpoint: float,
    band_bps: float,
    *,
    bids: bool,
) -> float:
    price_epsilon = midpoint * 1e-12
    if bids:
        boundary = midpoint * (1 - band_bps / 10_000)
        return sum(
            level.contracts
            for level in levels
            if level.price + price_epsilon >= boundary
        )

    boundary = midpoint * (1 + band_bps / 10_000)
    return sum(
        level.contracts for level in levels if level.price <= boundary + price_epsilon
    )


def calculate_liquidity_snapshot(
    order_book: FuturesOrderBook,
    side: AddOrderReq.SideEnum,
    requested_contracts: float,
    permitted_price_band_bps: float,
) -> LiquiditySnapshot:
    """Calculate size-aware execution and coarse depth metrics from one book."""
    if requested_contracts <= 0:
        raise ValueError("Requested contracts must be positive")
    if permitted_price_band_bps <= 0:
        raise ValueError("Permitted price band must be positive")

    best_bid = order_book.bids[0].price
    best_ask = order_book.asks[0].price
    midpoint = (best_bid + best_ask) / 2
    spread_bps = (best_ask - best_bid) / midpoint * 10_000

    bid_depth = {
        band: _depth_within_bps(
            order_book.bids,
            midpoint,
            band,
            bids=True,
        )
        for band in DEPTH_BANDS_BPS
    }
    ask_depth = {
        band: _depth_within_bps(
            order_book.asks,
            midpoint,
            band,
            bids=False,
        )
        for band in DEPTH_BANDS_BPS
    }

    depth_50_total = bid_depth[50] + ask_depth[50]
    book_imbalance = (
        (bid_depth[50] - ask_depth[50]) / depth_50_total if depth_50_total > 0 else None
    )

    if side == AddOrderReq.SideEnum.BUY:
        upper_boundary = midpoint * (1 + permitted_price_band_bps / 10_000)
        execution_levels = tuple(
            level
            for level in order_book.asks
            if level.price <= upper_boundary + midpoint * 1e-12
        )
    elif side == AddOrderReq.SideEnum.SELL:
        lower_boundary = midpoint * (1 - permitted_price_band_bps / 10_000)
        execution_levels = tuple(
            level
            for level in order_book.bids
            if level.price + midpoint * 1e-12 >= lower_boundary
        )
    else:
        raise ValueError(f"Unsupported futures order side: {side}")

    contracts_fillable = sum(level.contracts for level in execution_levels)
    execution_contracts = min(requested_contracts, contracts_fillable)
    remaining_contracts = execution_contracts
    fill_notional = 0.0
    worst_fill_price: float | None = None

    for level in execution_levels:
        level_fill = min(remaining_contracts, level.contracts)
        if level_fill <= 0:
            break
        fill_notional += level_fill * level.price
        remaining_contracts -= level_fill
        worst_fill_price = level.price
        if remaining_contracts <= 0:
            break

    expected_average_fill_price = (
        fill_notional / execution_contracts if execution_contracts > 0 else None
    )
    expected_slippage_bps: float | None = None
    if expected_average_fill_price is not None:
        if side == AddOrderReq.SideEnum.BUY:
            expected_slippage_bps = (
                (expected_average_fill_price - midpoint) / midpoint * 10_000
            )
        else:
            expected_slippage_bps = (
                (midpoint - expected_average_fill_price) / midpoint * 10_000
            )
        expected_slippage_bps = max(0.0, expected_slippage_bps)

    return LiquiditySnapshot(
        symbol=order_book.symbol,
        side=side,
        requested_contracts=requested_contracts,
        permitted_price_band_bps=permitted_price_band_bps,
        best_bid=best_bid,
        best_ask=best_ask,
        midpoint=midpoint,
        spread_bps=spread_bps,
        bid_depth_10_bps=bid_depth[10],
        ask_depth_10_bps=ask_depth[10],
        bid_depth_25_bps=bid_depth[25],
        ask_depth_25_bps=ask_depth[25],
        bid_depth_50_bps=bid_depth[50],
        ask_depth_50_bps=ask_depth[50],
        contracts_fillable=contracts_fillable,
        expected_average_fill_price=expected_average_fill_price,
        expected_slippage_bps=expected_slippage_bps,
        worst_fill_price=worst_fill_price,
        book_imbalance=book_imbalance,
        data_age_ms=order_book.data_age_ms,
    )
