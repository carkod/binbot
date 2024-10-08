import { intervalOptions } from "../../utils/validations"

export interface Bot {
  id: string
  name: string
  status: string
  balance_available: string
  balance_available_asset: string
  balance_size_to_use: number
  base_order_size: number
  balance_to_use: string
  errors: string[]
  mode: string
  max_so_count: string
  pair: string
  price_deviation_so: string
  so_size: string
  take_profit: number
  trailling: boolean
  trailling_deviation: number
  dynamic_trailling: boolean
  deal: any
  orders: any[]
  quoteAsset: string
  baseAsset: string
  stop_loss: number
  margin_short_reversal: boolean
  safety_orders: any[]
  cooldown: number
  strategy: string
  short_buy_price: number
  short_sell_price: number
  commissions: number
}

/**
 * This file contains redux state
 * that is shared between bots views
 * at the time of writing: bots and paper trading (test bots)
 */

// The initial state of the App
export const singleBot: Bot = {
  id: null,
  status: "inactive",
  balance_available: "0",
  balance_available_asset: "",
  balance_size_to_use: 0, // Centralized
  base_order_size: 50,
  balance_to_use: "USDC",
  errors: [],
  mode: "manual",
  max_so_count: "0",
  name: "Default bot",
  pair: "",
  price_deviation_so: "0.63",
  so_size: "0",
  take_profit: 2.3,
  trailling: false,
  trailling_deviation: 2.8,
  dynamic_trailling: false,
  deal: {},
  orders: [],
  quoteAsset: "",
  baseAsset: "",
  stop_loss: 3,
  margin_short_reversal: true,
  safety_orders: [],
  cooldown: 0,
  strategy: "long",
  short_buy_price: 0,
  short_sell_price: 0,
  commissions: 0,
};

const botsInitialState = {
  bot: singleBot,
  balanceAvailableError: false,
  candlestick_interval: intervalOptions[3],
  formIsValid: false,
}