import produce from "immer";
import { GET_TEST_AUTOTRADE_SETTINGS_SUCCESS } from "../../pages/paper-trading/actions";
import { checkValue } from "../../validations";
import {
  GET_TEST_AUTOTRADE_SETTINGS,
  SET_TEST_AUTOTRADE_SETTING,
} from "../paper-trading/actions";
import {
  ADD_BLACKLIST,
  ADD_BLACKLIST_ERROR,
  ADD_BLACKLIST_SUCCESS,
  DELETE_BLACKLIST,
  DELETE_BLACKLIST_ERROR,
  DELETE_BLACKLIST_SUCCESS,
  GET_BLACKLIST,
  GET_BLACKLIST_ERROR,
  GET_BLACKLIST_SUCCESS,
  GET_SETTINGS,
  GET_SETTINGS_ERROR,
  GET_SETTINGS_SUCCESS,
  SET_SETTINGS_STATE,
} from "./actions";

// The initial state of the App
export const initialState = {
  isError: false,
  data: null,
  message: null,
};

export const settingsReducerInitial = {
  candlestick_interval: "15m",
  autotrade: 0,
  max_request: 950,
  telegram_signals: 1,
  balance_to_use: "USDT",
  balance_size_to_use: 0,
  trailling: "true",
  take_profit: "",
  trailling_deviation: "",
  stop_loss: "",
};

const blacklistReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_BLACKLIST:
      return draft; // same as just 'return'
    case GET_BLACKLIST_SUCCESS:
      // OK: we return an entirely new state
      return {
        data: action.data,
      };
    case GET_BLACKLIST_ERROR:
      // OK: the immer way
      return;

    case ADD_BLACKLIST:
      return draft;
    case ADD_BLACKLIST_SUCCESS:
      if (!checkValue(action.data)) {
        draft.data.push(action.data);
        return {
          data: draft.data,
        };
      } else {
        return {
          data: draft.data,
        };
      }
    case ADD_BLACKLIST_ERROR:
      return;
    case DELETE_BLACKLIST:
      if (!checkValue(action.pair)) {
        return {
          data: draft.data.filter((x) => x !== action.pair),
        };
      } else {
        return draft.data;
      }
    case DELETE_BLACKLIST_SUCCESS:
      return action.payload;
    case DELETE_BLACKLIST_ERROR:
      return;
    default:
      break;
  }
}, {});

const settingsReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_SETTINGS:
      return draft; // same as just 'return'
    case GET_SETTINGS_SUCCESS:
      draft.settings = action.data
      return draft
    case SET_SETTINGS_STATE:
      const { payload } = action;
      draft.settings = { ...draft.settings, ...payload };
      return draft;
    case GET_TEST_AUTOTRADE_SETTINGS_SUCCESS:
      draft.test_autotrade_settings = action.data;
      return draft;
    case GET_TEST_AUTOTRADE_SETTINGS:
      return draft;
    case SET_TEST_AUTOTRADE_SETTING:
      for (const [key, value] of Object.entries(action.payload)) {
        draft.test_autotrade_settings[key] = value;
      }

      return draft;
    case GET_SETTINGS_ERROR:
      // OK: the immer way
      return;
    case DELETE_BLACKLIST:
      return draft; // same as just 'return'
    case DELETE_BLACKLIST_SUCCESS:
      // OK: we return an entirely new state
      return action.payload;
    case DELETE_BLACKLIST_ERROR:
      // OK: the immer way
      return;
    default:
      break;
  }
}, {settings: settingsReducerInitial});

export { blacklistReducer, settingsReducer };
