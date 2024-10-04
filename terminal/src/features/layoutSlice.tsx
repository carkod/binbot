import type { PayloadAction } from "@reduxjs/toolkit"
import { createAppSlice } from "../app/createAppSlice"

export interface LayoutInitialState {
  icon: string
  headerTitle: string
}

export const layoutInitialState: LayoutInitialState = {
  icon: "fas fa-home",
  headerTitle: "Dashboard",
}

export const layoutSlice = createAppSlice({
  name: "layout",
  initialState: layoutInitialState,
  reducers: {
    setHeaderContent(state, action: PayloadAction<LayoutInitialState>) {
      state.headerTitle = action.payload.headerTitle
      state.icon = action.payload.icon
    },
  },
  selectors: {
    selectHeaderTitle: (state) => state.headerTitle,
    selectHeaderIcon: (state) => state.icon,
  },
})

// Action creators are generated for each case reducer function.
export const { setHeaderContent } = layoutSlice.actions
export const { selectHeaderTitle, selectHeaderIcon } = layoutSlice.selectors