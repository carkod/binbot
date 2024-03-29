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
    inactive = "inactive"
    active = "active"
    completed = "completed"
    error = "error"
    archived = "archived"

class Strategy(str, Enum):
    long = "long"
    margin_short = "margin_short"

class OrderType(str, Enum):
    limit = "LIMIT"
    market= "MARKET"
    stop_loss = "STOP_LOSS"
    stop_loss_limit = "STOP_LOSS_LIMIT"
    take_profit = "TAKE_PROFIT"
    take_profit_limit = "TAKE_PROFIT_LIMIT"
    limit_maker = "LIMIT_MAKER"

    def __str__(self):
        return str(self.str)


class TimeInForce(str, Enum):
    gtc = "GTC"
    ioc = "IOC"
    fok = "FOK"

    def __str__(self):
        return str(self.str)

class OrderSide(str, Enum):
    buy = "BUY"
    sell = "SELL"

    def __str__(self):
        return str(self.str)

class CloseConditions(str, Enum):
    dynamic_trailling = "dynamic_trailling"
    timestamp = "timestamp" # No trailling, standard stop loss
    market_reversal = "market_reversal" # binbot-research param (self.market_trend_reversal)

    def __str__(self):
        return str(self.str)