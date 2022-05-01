import produce from "immer";
import {
  computeTotalProfit,
  filterByMonth,
  filterByWeek,
} from "../../state/bots/actions";
import { FILTER_BY_MONTH, FILTER_BY_WEEK } from "../../state/constants";
import { intervalOptions } from "../../validations";
import {
  ACTIVATE_TEST_BOT,
  ACTIVATE_TEST_BOT_ERROR,
  ACTIVATE_TEST_BOT_SUCCESS,
  CLOSE_TEST_BOT,
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
  SET_BOT_STATE,
} from "./actions";

// The initial state of the App
export const bot = {
  _id: null,
  status: "inactive",
  balance_available: "0",
  balance_available_asset: "",
  balanceAvailableError: false,
  balanceUsageError: false,
  balance_size_to_use: 0, // Centralized
  base_order_size: "",
  baseOrderSizeError: false,
  balance_to_use: "USDT",
  bot_profit: 0,
  mode: "manual",
  max_so_count: "0",
  maxSOCountError: false,
  name: "Default bot",
  nameError: false,
  pair: "",
  price_deviation_so: "0.63",
  priceDevSoError: false,
  so_size: "0",
  soSizeError: false,
  take_profit: "3",
  takeProfitError: false,
  trailling: "false",
  trailling_deviation: "0.63",
  traillingDeviationError: false,
  formIsValid: true,
  candlestick_interval: intervalOptions[3],
  deals: [],
  orders: [],
  quoteAsset: "",
  baseAsset: "",
  stop_loss: 0,
  stopLossError: false,
  safety_orders: {},
};

const initialState = {
  bot: bot,
  bots: [],
  totalProfit: 0,
};

const testBotsReducer = produce((draft, action) => {
  switch (action.type) {
    case SET_BOT_STATE:
      {
        const { payload } = action;
        draft.bot = { ...draft.bot, ...payload };
      }
      return draft;
    case GET_TEST_BOTS: {
      return draft;
    }
    case GET_TEST_BOTS_SUCCESS: {
      if (action.bots) {
        const filteredBots = filterByWeek(action.bots);
        draft.bots = filteredBots;
        draft.totalProfit = computeTotalProfit(filteredBots);
      } else {
        draft.bots = action.bots;
      }
      return draft;
    }

    case GET_TEST_BOTS_ERROR: {
      return {
        error: action.error,
      };
    }

    case GET_TEST_BOT: {
      return draft;
    }
    case GET_TEST_BOT_SUCCESS: {
      draft.bot = { ...draft.bot, ...action.bot };
      return draft;
    }

    case GET_TEST_BOT_ERROR: {
      return {
        error: action.error,
      };
    }

    case CREATE_TEST_BOT: {
      draft.bot = { ...draft.bot, ...action.bot };
      return draft;
    }
    case CREATE_TEST_BOT_SUCCESS: {
      draft.createdBotId = action.botId;
      return draft;
    }

    case CREATE_TEST_BOT_ERROR: {
      return draft;
    }

    case EDIT_TEST_BOT:
      draft.bot = { ...draft.bot, ...action.data };
      return draft;

    case EDIT_TEST_BOT_SUCCESS:
      draft.message = action.message;
      return draft;

    case EDIT_TEST_BOT_ERROR:
      return draft;

    case DELETE_TEST_BOT: {
      draft.removeId = action.removeId;
      return draft;
    }

    case DELETE_TEST_BOT_SUCCESS:
      draft.bots = draft.bots.filter(
        (x) => !x._id.$oid.includes(draft.removeId)
      );
      return draft;

    case CLOSE_TEST_BOT: {
      const newState = {
        data: draft.data,
        botActive: draft.botActive,
      };

      return newState;
    }

    case DELETE_TEST_BOT_ERROR: {
      return {
        error: action.error,
        botActive: draft.botActive,
      };
    }

    case ACTIVATE_TEST_BOT:
      return draft;

    case ACTIVATE_TEST_BOT_SUCCESS:
      return draft;

    case ACTIVATE_TEST_BOT_ERROR:
      return draft;

    case DEACTIVATE_TEST_BOT: {
      const newState = {
        data: draft.data,
        botActive: true,
      };

      return newState;
    }
    case DEACTIVATE_TEST_BOT_SUCCESS: {
      const findidx = draft.data.findIndex((x) => x._id.$oid === action.id);
      draft.data[findidx].status = "inactive";
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

    case FILTER_BY_WEEK:
      draft.bots = filterByWeek(draft.bots);
      return draft;

    case FILTER_BY_MONTH:
      draft.bots = filterByMonth(draft.bots);
      return draft;

    default:
      return draft;
  }
}, initialState);

export { testBotsReducer };
