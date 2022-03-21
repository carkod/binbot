import produce from "immer";
import { intervalOptions } from "../../validations";
import {
  ACTIVATE_TEST_BOT,
  ACTIVATE_TEST_BOT_ERROR,
  ACTIVATE_TEST_BOT_SUCCESS,
  CREATE_TEST_BOT,
  CREATE_TEST_BOT_ERROR,
  CREATE_TEST_BOT_SUCCESS,
  DEACTIVATE_TEST_BOT,
  DEACTIVATE_TEST_BOT_ERROR,
  DEACTIVATE_TEST_BOT_SUCCESS,
  DELETE_TEST_BOT,
  DELETE_TEST_BOT_ERROR,
  DELETE_TEST_BOT_SUCCESS,
  EDIT_TEST_BOT,
  EDIT_TEST_BOT_ERROR,
  EDIT_TEST_BOT_SUCCESS,
  GET_TEST_BOT,
  GET_TEST_BOTS,
  GET_TEST_BOTS_ERROR,
  GET_TEST_BOTS_SUCCESS,
  GET_TEST_BOT_ERROR,
  GET_TEST_BOT_SUCCESS,
  CLOSE_TEST_BOT,
} from "./actions";

// The initial state of the App
export const initialState = {
  _id: null,
  active: false,
  status: "inactive",
  balance_available: "0",
  balance_available_asset: "",
  balanceAvailableError: false,
  balanceUsageError: false,
  balance_usage_size: "100", // Centralized
  base_order_size: "",
  baseOrderSizeError: false,
  balance_to_use: "GBP",
  bot_profit: 0,
  max_so_count: "0",
  maxSOCountError: false,
  name: "Default bot",
  nameError: false,
  pair: "",
  price_deviation_so: "0.63",
  priceDevSoError: false,
  so_size: "0",
  soSizeError: false,
  start_condition: true,
  strategy: "long",
  take_profit: "3",
  takeProfitError: false,
  trailling: "false",
  trailling_deviation: "0.63",
  traillingDeviationError: false,
  formIsValid: true,
  activeTab: "main",
  candlestick_interval: intervalOptions[3],
  deals: [],
  orders: [],
  quoteAsset: "",
  baseAsset: "",
  stop_loss: 0,
  stopLossError: false,
  safety_orders: {},
};

const testBotsReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_TEST_BOTS: {
      return draft
    }
    case GET_TEST_BOTS_SUCCESS: {
      draft.bots = action.bots
      return draft;
    }

    case GET_TEST_BOTS_ERROR: {
      return {
        error: action.error,
      };
    }

    case CREATE_TEST_BOT: {
      const newState = {
        data: draft.data,
        botActive: false,
      };

      return newState;
    }
    case CREATE_TEST_BOT_SUCCESS: {
      const newState = {
        botId: action.botId,
        botActive: false,
        data: draft.data,
      };
      return newState;
    }

    case CREATE_TEST_BOT_ERROR: {
      return {
        error: action.error,
        botActive: false,
      };
    }

    case DELETE_TEST_BOT: {
      draft.removeId = action.removeId
      return draft;
    }

    case CLOSE_TEST_BOT: {
      const newState = {
        data: draft.data,
        botActive: draft.botActive,
      };

      return newState;
    }

    case DELETE_TEST_BOT_SUCCESS: {
      return draft;
    }

    case DELETE_TEST_BOT_ERROR: {
      return {
        error: action.error,
        botActive: draft.botActive,
      };
    }


    case DEACTIVATE_TEST_BOT: {
      const newState = {
        data: draft.data,
        botActive: true,
      };

      return newState;
    }
    case DEACTIVATE_TEST_BOT_SUCCESS: {
      const findidx = draft.data.findIndex(x => x._id.$oid === action.id);
      draft.data[findidx].status = "inactive"
      const newState = {
        data: draft.data,
        message: action.message,
        botActive: false,
      };
      return newState;
    }

    case DEACTIVATE_TEST_BOT_ERROR: {
      return {
        error: action.error,
        botActive: true,
      };
    }

    default:
      return draft;
  }
}, initialState);

export {
  testBotsReducer
};
