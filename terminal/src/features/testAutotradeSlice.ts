import {
  BinanceKlineintervals,
  CloseConditions,
  ExchangeId,
} from "../utils/enums";
import { createAppSlice } from "../app/createAppSlice";
import { type PayloadAction } from "@reduxjs/toolkit";
import type {
  AutotradeSettingsFormBoolean,
  AutotradeSettingsFormField,
} from "./autotradeSlice";
import { type AutotradeSettings } from "./autotradeApiSlice";

export const initialAutotradeSettings: AutotradeSettings = {
  id: "test_autotrade_settings",
  balance_size_to_use: 0,
  candlestick_interval: BinanceKlineintervals.ONE_HOUR,
  autotrade: true,
  trailing: true,
  trailing_deviation: 0,
  trailing_profit: 0,
  stop_loss: 0,
  take_profit: 0,
  fiat: "USDC",
  max_request: 0,
  telegram_signals: true,
  max_active_autotrade_bots: 0,
  grid_allocation_pct: 1.0,
  grid_cash_reserve_pct: 0.01,
  grid_total_margin: 1.0,
  grid_level_count: 3,
  grid_max_active_ladders: 3,
  max_margin_per_ladder_pct: 0.25,
  base_order_size: 0,
  updated_at: 0,
  close_condition: CloseConditions.DYNAMIC_TRAILING,
  autoswitch: false,
  exchange_id: ExchangeId.BINANCE,
};

// In general, this will be unused
// future plans include using it for bots e.g. to get fiat
// or default candlestick_interval for all bots
export const testAutotradeSettingsSlice = createAppSlice({
  name: "testAutotradeSettings",
  initialState: {
    settings: initialAutotradeSettings,
  },
  reducers: (create) => ({
    setTestSettingsField: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettingsFormField>) => {
        state.settings[payload.name] = payload.value;
      },
    ),
    setTestSettingsToggle: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettingsFormBoolean>) => {
        state.settings[payload.name] = payload.value;
      },
    ),
    setTestSettings: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettings>) => {
        state.settings = { ...initialAutotradeSettings, ...payload };
      },
    ),
  }),
  selectors: {
    selectTestSettings: (state) => state,
  },
});

export const { setTestSettingsField, setTestSettingsToggle, setTestSettings } =
  testAutotradeSettingsSlice.actions;
export const { selectTestSettings } = testAutotradeSettingsSlice.selectors;
