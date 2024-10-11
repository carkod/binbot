import type { PayloadAction } from "@reduxjs/toolkit"
import { createAppSlice } from "../../app/createAppSlice"
import { type Bot, singleBot } from "./botInitialState"

interface BotDetailsFormField {
  name: string
  value: string | number
}

interface BotDetailsFormFieldBoolean {
	name: string
	value: boolean
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
        state[payload.name] = payload.value
      },
    ),
		setToggle: create.reducer(
			(state, { payload }: PayloadAction<BotDetailsFormFieldBoolean>) => {
				state[payload.name] = payload.value
			}
		),
    setBot: create.reducer((state, { payload }: PayloadAction<BotDetailsState>) => {
      state = payload.bot
    }),
  }),
  selectors: {
    selectBot: state => {
      if (state) {
        return state
      } else {
        return singleBot
      }
    },
  },
})

export const { setField, setBot, setToggle } = botSlice.actions
export const { selectBot } = botSlice.selectors
