import type { ChartEditField } from "../../utils/charting/editing";
import type { PayloadAction } from "@reduxjs/toolkit";
import { createAppSlice } from "../../app/createAppSlice";
import { singleBot, type Bot, type RecoveryParams } from "./botInitialState";
import type {
  BotDetailsFormField,
  BotDetailsFormFieldBoolean,
  BotDetailsState,
} from "./bots";

export const botSlice = createAppSlice({
  name: "bot",
  initialState: {
    bot: singleBot,
    previewTrailingSettings: false,
    previewStopLossSettings: false,
    focusedOrderLine: null as ChartEditField | null,
  },
  reducers: (create) => ({
    focusOrderLine: create.reducer(
      (state, { payload }: PayloadAction<ChartEditField | null>) => {
        state.focusedOrderLine = payload;
        if (payload === "stop_loss") state.previewStopLossSettings = true;
        if (payload === "trailing_profit" || payload === "trailing_deviation")
          state.previewTrailingSettings = true;
      },
    ),
    setField: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormField>) => {
        state.bot[payload.name] = payload.value;
        if (payload.name === "stop_loss") state.previewStopLossSettings = true;
        if (
          payload.name === "trailing_profit" ||
          payload.name === "trailing_deviation"
        ) {
          state.previewTrailingSettings = true;
        }
      },
    ),
    setToggle: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormFieldBoolean>) => {
        state.bot[payload.name] = payload.value;
      },
    ),
    setRecoveryParams: create.reducer(
      (state, { payload }: PayloadAction<RecoveryParams | null>) => {
        if (payload !== null && state.bot.dynamic_position_sizing) return;
        state.bot.recovery_params = payload;
        if (payload === null) {
          state.bot.recovery_mode_id = null;
        }
      },
    ),
    setBot: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsState>) => {
        state.bot = { ...payload.bot };
        state.previewTrailingSettings = false;
        state.previewStopLossSettings = false;
        state.focusedOrderLine = null;
      },
    ),
    setCurrentPrice: create.reducer(
      (state, { payload }: PayloadAction<number>) => {
        // in principle this is updated only server-side,
        // but the streaming service can blip in performance
        state.bot.deal.current_price = payload;
      },
    ),
    resetBot: create.reducer((state, action?: PayloadAction<Partial<Bot>>) => {
      state.bot = {
        ...singleBot,
        ...(action?.payload || {}),
      };
      state.previewTrailingSettings = false;
      state.previewStopLossSettings = false;
      state.focusedOrderLine = null;
    }),
  }),
  selectors: {
    selectBot: (state) => {
      return state;
    },
  },
});

export const {
  setField,
  focusOrderLine,
  setBot,
  setToggle,
  setRecoveryParams,
  setCurrentPrice,
  resetBot,
} = botSlice.actions;
export const { selectBot } = botSlice.selectors;
