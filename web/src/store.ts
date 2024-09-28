import { configureStore } from "@reduxjs/toolkit";
import { reducer as toastrReducer } from "react-redux-toastr";
import loginReducer from "./containers/login/reducer";
import registrationReducer from "./containers/registration/reducer";
import { loadingReducer } from "./containers/spinner/reducer";
import {
  botReducer,
  candlestickReducer,
  symbolInfoReducer,
  symbolReducer,
  settingsReducer
} from "./state/bots/reducer";
import { testBotsReducer } from "./pages/paper-trading/reducer";
import { blacklistReducer } from "./pages/research/reducer";
import { balanceRawReducer, estimateReducer } from "./state/balances/reducer";
import {
  gainersLosersReducer,
  btcBenchmarkReducer,
  gainersLosersSeriesReducer,
} from "./pages/dashboard/reducer";
import { botsApi } from "./pages/bots/api";

export const store = configureStore({
  reducer: {
    // API slices
    [botsApi.reducerPath]: botsApi.reducer,

    // Reducer slices
    botReducer: botReducer.reducer,
    symbolInfoReducer: symbolInfoReducer.reducer,
    symbolReducer: symbolReducer.reducer,
    candlestickReducer: candlestickReducer.reducer,
    settingsReducer: settingsReducer.reducer,
    registrationReducer,
    loginReducer,
    balanceRawReducer,
    toastr: toastrReducer,
    loadingReducer,
    blacklistReducer,
    estimateReducer,
    testBotsReducer,
    gainersLosersReducer,
    btcBenchmarkReducer,
    gainersLosersSeriesReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;

export default store;
