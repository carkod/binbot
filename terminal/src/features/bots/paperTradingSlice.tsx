import type { PayloadAction } from "@reduxjs/toolkit";
import { createAppSlice } from "../../app/createAppSlice";
import { singleBot } from "./botInitialState";
import type {
  BotDetailsFormField,
  BotDetailsFormFieldBoolean,
  BotDetailsState,
} from "./bots";

export const paperTradingSlice = createAppSlice({
  name: "paperTrading",
  initialState: {
    paperTrading: singleBot,
  },
  reducers: (create) => ({
    setTestBotField: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormField>) => {
        state.paperTrading[payload.name] = payload.value;
      }
    ),
    setTestBotToggle: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormFieldBoolean>) => {
        state.paperTrading[payload.name] = payload.value;
      }
    ),
    setTestBot: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsState>) => {
        state.paperTrading = payload.bot;
      }
    ),
    setTestBotCurrentPrice: create.reducer(
      (state, { payload }: PayloadAction<number>) => {
        // in principle this is updated only server-side,
        // but the streaming service can blip in performance
        state.paperTrading.deal.current_price = payload;
      }
    ),
  }),
  selectors: {
    selectBot: (state) => {
      return state;
    },
  },
});

export const {
  setTestBotField,
  setTestBot,
  setTestBotToggle,
  setTestBotCurrentPrice,
} = paperTradingSlice.actions;
export const { selectBot } = paperTradingSlice.selectors;
