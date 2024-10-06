import type { PayloadAction } from "@reduxjs/toolkit"
import { createAppSlice } from "../../app/createAppSlice"
import { Bot, singleBot } from "./botInitialState"
import { userApiSlice } from "../userApiSlice"
import { botsApiSlice } from "./botsApiSlice"


export const botSlice = createAppSlice({
  name: "bot",
  // `createSlice` will infer the state type from the `initialState` argument
  initialState: singleBot,
  // The `reducers` field lets us define reducers and generate associated actions
  reducers: create => ({
    setField: create.reducer((state, payload) => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes
      state[payload.key] = payload.value
    }),
  }),
//   selectors: {
//     selectCount: counter => counter.value,
//     selectStatus: counter => counter.status,
//   },
})

// Action creators are generated for each case reducer function.
export const { setField } = botSlice.actions

// export const { selectCount, selectStatus } = counterSlice.selectors
