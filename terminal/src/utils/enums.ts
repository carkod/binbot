// Backend API types
// mostly copied from from api/tools/enum_definitions.py
// strings have to match exactly those in the back-end

export enum BotStatus {
  ALL = "all",
  INACTIVE = "inactive",
  ACTIVE = "active",
  PENDING = "pending",
  COMPLETED = "completed",
  CLOSED = "closed",
  ERROR = "error",
}

export enum EntryMode {
  IMMEDIATE = "immediate",
  CONDITIONAL_LIMIT = "conditional_limit",
}

export enum BotPosition {
  LONG = "long",
  SHORT = "short",
}

export enum DealType {
  CONVERSION = "conversion",
  BASE_ORDER = "base_order",
  TAKE_PROFIT = "take_profit",
  STOP_LOSS = "stop_loss",
  SHORT_SELL = "short_sell",
  SHORT_BUY = "short_buy",
  MARGIN_SHORT = "margin_short",
  PANIC_CLOSE = "panic_close",
  TRAILING_PROFIT = "trailing_profit",
  TRAILING_STOP_LOSS = "trailing_stop_loss",
  ALGORITHMIC_CLOSE = "algorithmic_close",
}

export enum TabsKeys {
  MAIN = "main",
  STOPLOSS = "stop-loss",
  TAKEPROFIT = "take-profit",
}

export enum CloseConditions {
  DYNAMIC_TRAILING = "dynamic_trailing",
  TIMESTAMP = "timestamp",
  MARKET_REVERSAL = "market_reversal",
}

export enum QuoteAsset {
  USDT = "USDT",
  USDC = "USDC",
  BTC = "BTC",
  ETH = "ETH",
  TRY = "TRY",
}

export enum ExchangeId {
  KUCOIN = "kucoin",
  BINANCE = "binance",
}

export enum MarketType {
  SPOT = "SPOT",
  MARGIN = "MARGIN",
  FUTURES = "FUTURES",
}
