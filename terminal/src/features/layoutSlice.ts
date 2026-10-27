import type { PayloadAction } from "@reduxjs/toolkit";
import { createAppSlice } from "../app/createAppSlice";

// Layout elements that
// can be dynamically changed by children components
export interface LayoutInitialState {
  icon?: string;
  headerTitle?: string;
  spinner?: boolean;
  botProgress?: { botId: string; percent: number; message: string } | null;
}

const initialState: LayoutInitialState = {
  icon: "fas fa-home",
  headerTitle: "Dashboard",
  spinner: false,
  botProgress: null,
};

export const layoutSlice = createAppSlice({
  name: "layout",
  initialState,
  reducers: (create) => ({
    setHeaderContent: create.reducer(
      (state, action: PayloadAction<LayoutInitialState>) => {
        state.headerTitle = action.payload.headerTitle;
        state.icon = action.payload.icon;
      },
    ),
    setSpinner: create.reducer(
      (state, action: PayloadAction<LayoutInitialState>) => {
        state.spinner = action.payload.spinner;
      },
    ),
    setBotProgress: create.reducer(
      (state, action: PayloadAction<LayoutInitialState["botProgress"]>) => {
        state.botProgress = action.payload;
      },
    ),
  }),
  selectors: {
    selectSpinner: (state, action) => (state.spinner = action.payload.spinner),
  },
});

export const { setHeaderContent, setSpinner, setBotProgress } =
  layoutSlice.actions;
