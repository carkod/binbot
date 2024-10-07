import type { PayloadAction } from "@reduxjs/toolkit"
import { createAppSlice } from "../../app/createAppSlice"
import { type Bot, singleBot } from "./botInitialState"

interface BotDetailsFormField {
  name: string
  value: string | number
}

interface BotDetailsState {
  bot: Bot
}

export const botSlice = createAppSlice({
  name: "bot",
  initialState: singleBot,
  reducers: create => ({
    setField: create.reducer(
      (state, { payload }: PayloadAction<BotDetailsFormField>) => {
        state[payload.name] = payload.name
      },
    ),
    setBot: create.reducer((state, { payload }: PayloadAction<BotDetailsState>) => {
      state = payload.bot
    }),
  }),
  selectors: {
    selectBot: state => state,
  },
})

export const { setField, setBot } = botSlice.actions
export const { selectBot } = botSlice.selectors
