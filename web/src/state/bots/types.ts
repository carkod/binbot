/**
 * Enums for bot status
 * refer to api/bots/schema.py
 */
enum BotStatus {
  active = "active",
  inactive = "inactive",
  completed = "completed",
  error = "error",
  archived = "archived",
}

enum BotStrategy {
  long = "long",
  margin_short = "margin_short",
}

enum BotMode {
  manual = "manual",
  autotrade = "autotrade",
}

/**
 * Enums for candlestick intervals
 * from Binance
 */
enum IntervalOptions {
  oneMinute = "1m",
  threeMinutes = "3m",
  fiveMinutes = "5m",
  fifteenMinutes = "15m",
  thirtyMinutes = "30m",
  oneHour = "1h",
  twoHours = "2h",
  fourHours = "4h",
  sixHours = "6h",
  eightHours = "8h",
  twelveHours = "12h",
  oneDay = "1d",
  threeDays = "3d",
  oneWeek = "1w",
  oneMonth = "1M",
}
interface Deal {
  buy_price: number;
  buy_total_qty: number;
  buy_timestamp: number;
  current_price: number;
  sd: number;
  avg_buy_price: number;
  take_profit_price: number;
  sell_timestamp: number;
  sell_price: number;
  sell_qty: number;
  trailling_stop_loss_price: number;
  trailling_profit_price: number;
  stop_loss_price: number;
  trailling_profit: number;
  so_prices: number;
  margin_short_loan_principal: number;
  margin_loan_id: number;
  hourly_interest_rate: number;
  margin_short_sell_price: number;
  margin_short_loan_interest: number;
  margin_short_buy_back_price: number;
  margin_short_sell_qty: number;
  margin_short_buy_back_timestamp: number;
  margin_short_base_order: number;
  margin_short_sell_timestamp: number | string;
  margin_short_loan_timestamp: number | string;
}

/**
 * This file contains redux state
 * that is shared between bots views
 * at the time of writing: bots and paper trading (test bots)
 */

export interface Bot {
  id: string | null;
  status: BotStatus;
  balance_available: string;
  balance_available_asset: string;
  base_order_size: number;
  balance_to_use: string;
  errors: string[];
  baseOrderSizeError: boolean;
  balanceAvailableError: boolean;
  balanceUsageError: boolean;
  balance_size_to_use: number;
  max_so_count: string;
  maxSOCountError: boolean;
  mode: BotMode;
  name: string;
  nameError: boolean;
  pair: string;
  price_deviation_so: string;
  priceDevSoError: boolean;
  so_size: string;
  soSizeError: boolean;
  take_profit: number;
  takeProfitError: boolean;
  trailling: string;
  trailling_deviation: number;
  dynamic_trailling: boolean;
  traillingDeviationError: boolean;
  formIsValid: boolean;
  candlestick_interval: string;
  deal: Deal; // Handled server side, shouldn't be changed in the client
  strategy: BotStrategy;
  orders: object[];
  quoteAsset: string;
  baseAsset: string;
  stop_loss: number;
  margin_short_reversal: boolean;
  stopLossError: boolean;
  safety_orders: object[];
  addAllError: string;
  cooldown: number;
  marginShortError: string | null;
  short_buy_price: number;
  short_sell_price: number;
}

// The initial state of the App
export const bot: Bot = {
  id: null,
  status: BotStatus.inactive,
  balance_available: "0",
  balance_available_asset: "",
  balanceAvailableError: false,
  balanceUsageError: false,
  balance_size_to_use: 0, // Centralized
  base_order_size: 50,
  baseOrderSizeError: false,
  balance_to_use: "USDC",
  errors: [],
  mode: BotMode.manual,
  max_so_count: "0",
  maxSOCountError: false,
  name: "Default bot",
  nameError: false,
  pair: "",
  price_deviation_so: "0.63",
  priceDevSoError: false,
  so_size: "0",
  soSizeError: false,
  take_profit: 2.3,
  takeProfitError: false,
  trailling: "false",
  trailling_deviation: 2.8,
  dynamic_trailling: false,
  traillingDeviationError: false,
  formIsValid: true,
  candlestick_interval: IntervalOptions.fifteenMinutes,
  deal: {
    buy_price: 0,
    buy_total_qty: 0,
    buy_timestamp: 0,
    current_price: 0,
    sd: 0,
    avg_buy_price: 0,
    take_profit_price: 0,
    sell_timestamp: 0,
    sell_price: 0,
    sell_qty: 0,
    trailling_stop_loss_price: 0,
    trailling_profit_price: 0,
    stop_loss_price: 0,
    trailling_profit: 0,
    so_prices: 0,
    margin_short_loan_principal: 0,
    margin_loan_id: 0,
    hourly_interest_rate: 0,
    margin_short_sell_price: 0,
    margin_short_loan_interest: 0,
    margin_short_buy_back_price: 0,
    margin_short_sell_qty: 0,
    margin_short_buy_back_timestamp: 0,
    margin_short_base_order: 0,
    margin_short_sell_timestamp: 0,
    margin_short_loan_timestamp: 0,
  },
  orders: [],
  quoteAsset: "",
  baseAsset: "",
  stop_loss: 3,
  margin_short_reversal: true,
  stopLossError: false,
  safety_orders: [],
  addAllError: "",
  cooldown: 0,
  strategy: BotStrategy.long,
  marginShortError: null,
  short_buy_price: 0,
  short_sell_price: 0,
};


export type FilterParams = {
  startDate: string | null;
  endDate: string | null;
};

export type BotState = {
  bots?: Bot[];
  bot_profit?: number;
  bot?: Bot;
  data?: any;
  message: string;
  botId?: string;
  totalProfit?: number;
  params?: FilterParams;
  botActive?: boolean;
  removeId?: string;
  error?: number;
};

export interface BotPayload {
  params?: FilterParams;
  bots?: Bot[];
  error?: number;
  removeId?: string;
  message?: string;
  data?: any;
  id?: string;
  botId?: string;
}

export interface SettingsState {
  candlestick_interval: string;
  autotrade: number;
  max_request: number;
  telegram_signals: number;
  balance_to_use: string;
  balance_size_to_use: number;
  trailling: string;
  take_profit: number;
  trailling_deviation: number;
  stop_loss: number;
  data?: object | Array<object> | null;
}
