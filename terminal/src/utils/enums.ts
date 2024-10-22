// Backend API types
// mostly copied from from api/tools/enum_definitions.py
// strings have to match exactly those in the back-end

export enum BotStatus {
  INACTIVE = "inactive",
  ACTIVE = "active",
  COMPLETED = "completed",
  ERROR = "error",
  ARCHIVED = "archived",
}

export enum BotMode {
  MANUAL = "manual",
  AUTO = "auto",
}

export enum BotStrategy {
  LONG = "long",
  MARGIN_SHORT = "margin_short",
}

export enum DealType {
  BASE_ORDER = "base_order",
  TAKE_PROFIT = "take_profit",
  STOP_LOSS = "stop_loss",
  SHORT_SELL = "short_sell",
  SHORT_BUY = "short_buy",
  MARGIN_SHORT = "margin_short",
  PANIC_CLOSE = "panic_close",
  TRAILLING_PROFIT = "trailling_profit",
  TRAILLING_STOP_LOSS = "trailling_stop_loss",
}

export enum BinanceKlineintervals {
  ONE_MINUTE = "1m",
  THREE_MINUTES = "3m",
  FIVE_MINUTES = "5m",
  FIFTEEN_MINUTES = "15m",
  THIRTY_MINUTES = "30m",
  ONE_HOUR = "1h",
  TWO_HOURS = "2h",
  FOUR_HOURS = "4h",
  SIX_HOURS = "6h",
  EIGHT_HOURS = "8h",
  TWELVE_HOURS = "12h",
  ONE_DAY = "1d",
  THREE_DAYS = "3d",
  ONE_WEEK = "1w",
  ONE_MONTH = "1M",
}

export enum TabsKeys {
  MAIN = "main",
  STOPLOSS = "stop-loss",
  TAKEPROFIT = "take-profit",
}
