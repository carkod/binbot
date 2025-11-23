import {
  BinanceKlineintervals,
  CloseConditions,
  ExchangeId,
} from "../utils/enums";
import { createAppSlice } from "../app/createAppSlice";
import { type AutotradeSettings } from "./autotradeApiSlice";
import { type PayloadAction } from "@reduxjs/toolkit";

export const initialAutotradeSettings: AutotradeSettings = {
  id: "autotrade_settings",
  candlestick_interval: BinanceKlineintervals.ONE_HOUR,
  autotrade: true,
  trailling: true,
  trailling_deviation: 0,
  trailling_profit: 0,
  stop_loss: 0,
  take_profit: 0,
  fiat: "USDC",
  balance_size_to_use: 0,
  max_request: 0,
  telegram_signals: true,
  max_active_autotrade_bots: 0,
  base_order_size: 0,
  updated_at: 0,
  close_condition: CloseConditions.DYNAMIC_TRAILLING,
  autoswitch: false,
  exchange_id: ExchangeId.BINANCE,
};

export interface AutotradeSettingsFormField {
  name: string;
  value: string | number;
}

export interface AutotradeSettingsFormBoolean {
  name: string;
  value: boolean;
}

// In general, this will be unused
// future plans include using it for bots e.g. to get fiat
// or default candlestick_interval for all bots
export const autotradeSettingsSlice = createAppSlice({
  name: "autotradeSettings",
  initialState: {
    settings: initialAutotradeSettings,
  },
  reducers: (create) => ({
    setSettingsField: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettingsFormField>) => {
        state.settings[payload.name] = payload.value;
      },
    ),
    setSettingsToggle: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettingsFormBoolean>) => {
        state.settings[payload.name] = payload.value;
      },
    ),
    setSettings: create.reducer(
      (state, { payload }: PayloadAction<AutotradeSettings>) => {
        state.settings = payload;
      },
    ),
  }),
  selectors: {
    selectSettings: (state) => state,
  },
});

export const { setSettingsField, setSettingsToggle, setSettings } =
  autotradeSettingsSlice.actions;
export const { selectSettings } = autotradeSettingsSlice.selectors;
