from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from pydantic import BaseModel, ConfigDict


class OrderBookLevel(BaseModel):
    model_config = ConfigDict(frozen=True)

    price: float
    contracts: float


class FuturesOrderBook(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    exchange_timestamp_ms: int
    received_timestamp_ms: int

    @property
    def data_age_ms(self) -> int:
        return max(0, self.received_timestamp_ms - self.exchange_timestamp_ms)


class LiquiditySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: AddOrderReq.SideEnum
    requested_contracts: float
    permitted_price_band_bps: float
    best_bid: float
    best_ask: float
    midpoint: float
    spread_bps: float
    bid_depth_10_bps: float
    ask_depth_10_bps: float
    bid_depth_25_bps: float
    ask_depth_25_bps: float
    bid_depth_50_bps: float
    ask_depth_50_bps: float
    contracts_fillable: float
    expected_average_fill_price: float | None
    expected_slippage_bps: float | None
    worst_fill_price: float | None
    book_imbalance: float | None
    data_age_ms: int
