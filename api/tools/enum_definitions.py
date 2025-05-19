from enum import Enum


class EnumDefinitions:
    """
    Enums established by Binance API
    """

    symbol_status = (
        "PRE_TRADING",
        "TRADING",
        "POST_TRADING",
        "END_OF_DAY",
        "HALT",
        "AUCTION_MATCH",
        "BREAK",
    )
    symbol_type = "SPOT"
    order_status = [
        "NEW",
        "PARTIALLY_FILLED",
        "FILLED",
        "CANCELED",
        "REJECTED",
        "EXPIRED",
    ]
    chart_intervals = (
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    )
    rate_limit_intervals = ("SECOND", "MINUTE", "DAY")
    order_book_limits = ("5", "10", "20", "50", "100", "500", "1000", "5000")


class BinbotEnums:
    statuses = ("inactive", "active", "completed", "error", "archived")
    mode = ("manual", "autotrade")
    strategy = ("long", "short", "margin_long", "margin_short")


class Status(str, Enum):
    all = "all"
    inactive = "inactive"
    active = "active"
    completed = "completed"
    error = "error"


class Strategy(str, Enum):
    long = "long"
    margin_short = "margin_short"


class OrderType(str, Enum):
    limit = "LIMIT"
    market = "MARKET"
    stop_loss = "STOP_LOSS"
    stop_loss_limit = "STOP_LOSS_LIMIT"
    take_profit = "TAKE_PROFIT"
    take_profit_limit = "TAKE_PROFIT_LIMIT"
    limit_maker = "LIMIT_MAKER"


class TimeInForce(str, Enum):
    gtc = "GTC"
    ioc = "IOC"
    fok = "FOK"


class OrderSide(str, Enum):
    buy = "BUY"
    sell = "SELL"


class OrderStatus(str, Enum):
    new = "NEW"
    partially_filled = "PARTIALLY_FILLED"
    filled = "FILLED"
    canceled = "CANCELED"
    rejected = "REJECTED"
    expired = "EXPIRED"


class CloseConditions(str, Enum):
    dynamic_trailling = "dynamic_trailling"
    timestamp = "timestamp"  # No trailling, standard stop loss
    market_reversal = (
        "market_reversal"  # binbot-research param (self.market_trend_reversal)
    )


class TrendEnum(str, Enum):
    up_trend = "uptrend"
    down_trend = "downtrend"
    neutral = None


class KafkaTopics(str, Enum):
    klines_store_topic = "klines-store-topic"
    technical_indicators = "technical-indicators"
    signals = "signals"
    restart_streaming = "restart-streaming"
    restart_autotrade = "restart-autotrade"


class DealType(str, Enum):
    base_order = "base_order"
    take_profit = "take_profit"
    stop_loss = "stop_loss"
    short_sell = "short_sell"
    short_buy = "short_buy"
    margin_short = "margin_short"
    panic_close = "panic_close"
    trailling_profit = "trailling_profit"


class BinanceKlineIntervals(str, Enum):
    one_minute = "1m"
    three_minutes = "3m"
    five_minutes = "5m"
    fifteen_minutes = "15m"
    thirty_minutes = "30m"
    one_hour = "1h"
    two_hours = "2h"
    four_hours = "4h"
    six_hours = "6h"
    eight_hours = "8h"
    twelve_hours = "12h"
    one_day = "1d"
    three_days = "3d"
    one_week = "1w"
    one_month = "1M"

    def bin_size(self):
        return int(self.value[:-1])

    def unit(self):
        if self.value[-1:] == "m":
            return "minute"
        elif self.value[-1:] == "h":
            return "hour"
        elif self.value[-1:] == "d":
            return "day"
        elif self.value[-1:] == "w":
            return "week"
        elif self.value[-1:] == "M":
            return "month"


class AutotradeSettingsDocument(str, Enum):
    # Autotrade settings for test bots
    test_autotrade_settings = "test_autotrade_settings"
    # Autotrade settings for real bots
    settings = "autotrade_settings"


class UserRoles(str, Enum):
    # Full access to all resources
    user = "user"
    # Access to terminal and customer accounts
    admin = "admin"
    # Only access to funds and client website
    customer = "customer"
