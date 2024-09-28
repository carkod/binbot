import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import {
  computeSingleBotProfit,
  computeTotalProfit,
} from "./actions";
import { BotState, BotPayload, SettingsState } from "./types";
import { addNotification } from "../../validations";

// The initial state of the App
export const initialState: BotState = {
  bots: [],
  bot_profit: 0, // separate state to avoid tick re-rendering
  bot: null,
  data: null,
  message: null,
  botId: null,
  params: {
    startDate: null,
    endDate: null,
  },
};

const settingsReducerInitial: SettingsState = {
  candlestick_interval: "15m",
  autotrade: 0,
  max_request: 950,
  telegram_signals: 1,
  balance_to_use: "USDC",
  balance_size_to_use: 0,
  trailling: "true",
  take_profit: 0,
  trailling_deviation: 0,
  stop_loss: 0,
};

/**
 * Handle notification messages
 * HTTP 200 errors with error message
 * this differs from the error message from the server
 * which can be 422, 404, 500 etc which are handled by
 * getBotsError, deleteBotError, activateBotError, deactivateBotError, createBotError...
 * @param payload: BotPayload
**/
function handleNotifications({ payload }) {
  if (payload.error === 1) {
    addNotification("Some errors encountered", payload.message, "error");
  } else {
    addNotification("SUCCESS!", payload.message, "success");
  }
}

const botReducer = createSlice({
  name: "bot",
  initialState,
  reducers: {
    getBots(state: BotState, action: PayloadAction<BotPayload>) {
      if (action.payload.params) {
        state.params.startDate = action.payload.params.startDate;
        state.params = action.payload.params;
      } else {
        state.params = initialState.params;
      }
      return state;
    },
    getBotsSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      if (action.payload.bots) {
        state.bots = action.payload.bots;
        state.totalProfit = computeTotalProfit(action.payload.bots);
      } else {
        state.bots = action.payload.bots;
      }
      return state;
    },
    getBotsError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
      return state;
    },
    deleteBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.removeId = action.payload.removeId;
      return state;
    },
    deleteBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      const bots = state.bots.filter((x) => !x.id.includes(state.removeId));
      state.bots = bots;
      state.totalProfit = computeTotalProfit(bots);
      return state;
    },
    deleteBotError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
    },
    activateBot(state: BotState) {
      return state;
    },
    activateBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.message = action.payload.message;
      state.botId = action.payload.data;
      return state;
    },
    activateBotError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
      state.botActive = false;
    },
    deactivateBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.data = action.data;
      state.botActive = true;
    },
    deactivateBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      const findidx = state.data.findIndex((x) => x.id === action.id);
      state.data[findidx].status = "inactive";
      const newState = {
        data: state.data,
        message: action.payload.message,
        botActive: false,
      };
      return newState;
    },
    deactivateBotError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
      state.botActive = true;
    },
    editBot(state: BotState) {
      return state;
    },
    editBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      const findidx = state.data.findIndex((x) => x.id === action.payload.id);
      handleNotifications(action);
      state.data[findidx] = action.payload.data;
      return state;
    },
    createBot(state: BotState) {
      return state;
    },
    createBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.botId = action.payload.botId;
      return state;
    },
    createBotError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
      state.botActive = false;
    },
    setBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.bot = action.payload.data;
      return state;
    },
    resetBot(state: BotState) {
      state.bot = initialState.bot;
      return state;
    },
    getBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.bots = action.payload.bots;
      state.bot_profit = computeSingleBotProfit(action.payload.bots);
      return state;
    },
    getBotError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
    },
  },
});

const symbolReducer = createSlice({
  name: "symbol",
  initialState,
  reducers: {
    getSymbols(state: BotState) {
      return state;
    },
    getSymbolsSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.data = action.payload.data;
      return state;
    },
    getSymbolsError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
    },
  },
});

const symbolInfoReducer = createSlice({
  name: "symbolInfo",
  initialState,
  reducers: {
    getSymbolInfo(state: BotState) {
      return state;
    },
    getSymbolInfoSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.data = action.payload.data;
      return state;
    },
    getSymbolInfoError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
    },
  },
});

const candlestickReducer = createSlice({
  name: "candlestick",
  initialState,
  reducers: {
    loadCandlestick(state: BotState) {
      return state;
    },
    loadCandlestickSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.data = action.payload.data;
      return state;
    },
    loadCandlestickError(state: BotState, action: PayloadAction<BotPayload>) {
      state.error = action.payload.error;
    },
  },
});

const settingsReducer = createSlice({
  name: "settings",
  initialState: settingsReducerInitial,
  reducers: {
    getSettings(state: SettingsState) {
      return state;
    },
    getSettingsSuccess(state: SettingsState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.data = action.payload.data;
      return state;
    },
    setSettingsState(state: SettingsState, action: PayloadAction<BotPayload>) {
      handleNotifications(action);
      state.data = { ...state.data, ...action };
      return state;
    },
  },
});

export {
  botReducer,
  symbolReducer,
  symbolInfoReducer,
  candlestickReducer,
  settingsReducer,
};
