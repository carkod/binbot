import { CaseReducer, createSlice, PayloadAction, Slice } from '@reduxjs/toolkit'
import {
  Bot,
  bot,
  computeSingleBotProfit,
  computeTotalProfit,
} from "../../state/bots/actions";
import {
  GET_TEST_AUTOTRADE_SETTINGS,
  GET_TEST_AUTOTRADE_SETTINGS_SUCCESS,
  SET_TEST_AUTOTRADE_SETTING,
} from "../paper-trading/actions";
import {
  ACTIVATE_BOT,
  ACTIVATE_BOT_ERROR,
  ACTIVATE_BOT_SUCCESS,
  ARCHIVE_BOT,
  ARCHIVE_BOT_SUCCESS,
  CLOSE_BOT,
  CREATE_BOT,
  CREATE_BOT_ERROR,
  CREATE_BOT_SUCCESS,
  DEACTIVATE_BOT,
  DEACTIVATE_BOT_ERROR,
  DEACTIVATE_BOT_SUCCESS,
  DELETE_BOT,
  DELETE_BOT_ERROR,
  DELETE_BOT_SUCCESS,
  EDIT_BOT,
  EDIT_BOT_SUCCESS,
  GET_BOTS,
  GET_BOTS_ERROR,
  GET_BOTS_SUCCESS,
  GET_BOT_SUCCESS,
  GET_SETTINGS,
  GET_SETTINGS_SUCCESS,
  GET_SYMBOLS,
  GET_SYMBOLS_ERROR,
  GET_SYMBOLS_SUCCESS,
  GET_SYMBOL_INFO,
  GET_SYMBOL_INFO_ERROR,
  GET_SYMBOL_INFO_SUCCESS,
  LOAD_CANDLESTICK,
  LOAD_CANDLESTICK_ERROR,
  LOAD_CANDLESTICK_SUCCESS,
  SET_BOT,
  SET_SETTINGS_STATE,
  RESET_BOT,
} from "./actions";

type BotState = {
  bots: any[];
  bot_profit: number;
  errorBots: any[];
  bot: any;
  data: any;
  message: string;
  botId: string;
  totalProfit?: number;
  params: {
    startDate: string | null;
    endDate: string | null;
  };
};


interface BotPayload {
  params?: any;
  bots?: Bot[];
  error?: string;
  removeId?: string;
  message?: string;
  data?: string | Bot;
  id?: string;
}


// The initial state of the App
export const initialState: BotState = {
  bots: [],
  bot_profit: 0, // separate state to avoid tick re-rendering
  errorBots: [],
  bot: bot,
  data: null,
  message: null,
  botId: null,
  params: {
    startDate: null,
    endDate: null,
  },
};

export const settingsReducerInitial = {
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

export const botReducer = createSlice({
  name: "bot",
  initialState,
  reducers: {
    getBots(state: BotState, action: PayloadAction<BotPayload>)  {
      if (action.payload.params) {
        state.params = action.payload.params;
      } else {
        state.params = initialState.params;
      }
      return state;
    },
    getBotsSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      if (action.payload.bots) {
        state.bots = action.payload.bots;
        state.errorBots = action.payload.bots.filter((x) => x.status === "error");
        state.totalProfit = computeTotalProfit(action.payload.bots);
      } else {
        state.bots = action.payload.bots;
      }
      return state;
    },
    getBotsError(state: BotState, action: PayloadAction<BotPayload>) {
      return {
        error: action.error,
      };
    },
    deleteBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.removeId = action.removeId;
      return state;
    },
    deleteBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      let bots = state.bots.filter((x) => !x.id.includes(state.removeId));
      state.bots = bots;
      state.totalProfit = computeTotalProfit(bots);
      return state;
    },
    deleteBotError(state: BotState, action: PayloadAction<BotPayload>) {
      return {
        error: action.error,
        botActive: state.botActive,
      };
    },
    closeBot(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    activateBot(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    activateBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      state.message = action.message;
      state.botId = action.data;
      return state;
    },
    activateBotError(state: BotState, action: PayloadAction<BotPayload>) { {
      return {
        error: action.error,
        botActive: false,
      };
    },
    deactivateBot(state: BotState, action: PayloadAction<BotPayload>) {
      const newState = {
        data: state.data,
        botActive: true,
      };

      return newState;
    },
    deactivateBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      const findidx = state.data.findIndex((x) => x.id === action.id);
      state.data[findidx].status = "inactive";
      const newState = {
        data: state.data,
        message: action.message,
        botActive: false,
      };
      return newState;
    },
    deactivateBotError(state: BotState, action: PayloadAction<BotPayload>) {) {
      return {
        error: action.error,
        botActive: true,
      };
    },
    editBot(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    editBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      const findidx = state.data.findIndex((x) => x.id === action.id);
      state.data[findidx] = action.data;
      return state;
    },
    createBot(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    createBotSuccess(state: BotState, action: PayloadAction<BotPayload>) { {
      state.botId = action.botId;
      return state;
    },
    createBotError(state: BotState, action: PayloadAction<BotPayload>) {
      return {
        error: action.error,
        botActive: false,
      };
    },
    setBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.bot = action.data;
      return state;
    },
    resetBot(state: BotState, action: PayloadAction<BotPayload>) {
      state.bot = initialState.bot;
      return state;
    },
    getBotSuccess(state: BotState, action: PayloadAction<BotPayload>) {
      state.bot = action.bots;
      state.bot_profit = computeSingleBotProfit(action.bots);
      return state;
    },
    getBotError(state: BotState, action: PayloadAction<BotPayload>) {
      return {
        error: action.error,
      };
    },
  },
});


export const symbolReducer = createSlice({
  name: "symbol",
  initialState,
  reducers: {
    getSymbols(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    getSymbolsSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      state.data = action.data;
      return state;
    },
    getSymbolsError(state: BotState, action: PayloadAction<BotPayload>) {{
      return {
        error: action.error,
      };
    },
  },
});

export const symbolInfoReducer = createSlice({
  name: "symbolInfo",
  initialState,
  reducers: {
    getSymbolInfo(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    getSymbolInfoSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      state.data = action.data;
      return state;
    },
    getSymbolInfoError(state: BotState, action: PayloadAction<BotPayload>) {) {
      return {
        error: action.error,
      };
    },
  },
});

export const candlestickReducer = createSlice({
  name: "candlestick",
  initialState,
  reducers: {
    loadCandlestick(state: BotState, action: PayloadAction<BotPayload>) {{
      return state;
    },
    loadCandlestickSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      state.data = action.data;
      return state;
    },
    loadCandlestickError(state: BotState, action: PayloadAction<BotPayload>) {) {
      return {
        error: action.error,
      };
    },
  },
});

export const settingsReducer = createSlice({
  name: "settings",
  initialState,
  reducers: {
    getSettings(state: BotState, action: PayloadAction<BotPayload>) {
      return state;
    },
    getSettingsSuccess(state: BotState, action: PayloadAction<BotPayload>) {) {
      state.data = action.data;
      return state;
    },
    setSettingsState(state: BotState, action: PayloadAction<BotPayload>) { {
      state.data = { ...state.data, ...action.payload };
      return state;
    },
  },
});
