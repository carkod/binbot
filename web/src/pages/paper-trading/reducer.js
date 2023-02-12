import produce from "immer";
import { bot, computeSingleBotProfit, computeTotalProfit } from "../../state/bots/actions";
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
        draft.bots = action.bots;
        draft.totalProfit = computeTotalProfit(action.bots);
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
      action.bot.bot_profit = computeSingleBotProfit(action.bot)
      draft.bot = { ...draft.bot, ...action.bot };
      return draft;
    }

    case GET_TEST_BOT_ERROR: {
      return {
        error: action.error,
      };
    }

    case CREATE_TEST_BOT: {
      action.bot.bot_profit = computeSingleBotProfit(action.bot)
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
      action.data.bot_profit = computeSingleBotProfit(action.bot)
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
      let bots = draft.bots.filter(
        (x) => !x.id.includes(draft.removeId)
      );
      draft.bots = bots;
      draft.totalProfit = computeTotalProfit(bots);
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
      const findidx = draft.data.findIndex((x) => x.id === action.id);
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

    default:
      return draft;
  }
}, initialState);

export { testBotsReducer };
