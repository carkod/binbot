import type { PayloadAction } from "@reduxjs/toolkit";
import { createAppSlice } from "../../app/createAppSlice";
import { type Bot, singleBot } from "./botInitialState";

interface BotDetailsFormField {
  name: string;
  value: string | number;
}

interface BotDetailsFormFieldBoolean {
  name: string;
  value: boolean;
}

interface BotDetailsState {
  bot: Bot;
}

export const botSlice = createAppSlice({
  name: "bot",
  initialState: {
    bot: singleBot,
  },
  reducers: (create) => ({
    setField: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormField>) => {
        state.bot[payload.name] = payload.value;
      },
    ),
    setToggle: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormFieldBoolean>) => {
        state.bot[payload.name] = payload.value;
      },
    ),
    setBot: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsState>) => {
        state.bot = payload.bot;
      },
    ),
    setCurrentPrice: create.reducer(
      (state, { payload }: PayloadAction<number>) => {
        // in principle this is updated only server-side,
        // but the streaming service can blip in performance
        state.bot.deal.current_price = payload;
      },
    ),
  }),
  selectors: {
    selectBot: (state) => {
      return state;
    },
  },
});

export const { setField, setBot, setToggle, setCurrentPrice } =
  botSlice.actions;
export const { selectBot } = botSlice.selectors;
