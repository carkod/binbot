import produce from "immer";
import { bot, computeTotalProfit } from "../../state/bots/actions";
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
} from "./actions";

// The initial state of the App
export const initialState = {
  bot: bot,
  data: null,
  message: null,
  botId: null,
  params: {
    startDate: null,
    endDate: null,
  },
};

const botReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_BOTS: {
      if (action.params) {
        draft.params = action.params;
      } else {
        draft.params = initialState.params;
      }
      return draft;
    }
    case GET_BOTS_SUCCESS: {
      if (action.bots) {
        draft.bots = action.bots;
        draft.totalProfit = computeTotalProfit(action.bots);
      } else {
        draft.bots = action.bots;
      }
      return draft;
    }

    case GET_BOTS_ERROR: {
      return {
        error: action.error,
      };
    }

    case DELETE_BOT: {
      draft.removeId = action.removeId;
      return draft;
    }

    case DELETE_BOT_SUCCESS:
      let bots = draft.bots.filter(
        (x) => !x._id.$oid.includes(draft.removeId)
      );
      draft.bots = bots;
      draft.totalProfit = computeTotalProfit(bots);
      return draft;

    case DELETE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: draft.botActive,
      };
    }

    case CLOSE_BOT: {
      return draft;
    }

    case ACTIVATE_BOT: {
      return draft;
    }
    case ACTIVATE_BOT_SUCCESS: {
      draft.message = action.message;
      draft.botId = action.data;
      return draft;
    }

    case ACTIVATE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: false,
      };
    }

    case DEACTIVATE_BOT: {
      const newState = {
        data: draft.data,
        botActive: true,
      };

      return newState;
    }
    case DEACTIVATE_BOT_SUCCESS: {
      const findidx = draft.data.findIndex((x) => x._id.$oid === action.id);
      draft.data[findidx].status = "inactive";
      const newState = {
        data: draft.data,
        message: action.message,
        botActive: false,
      };
      return newState;
    }

    case DEACTIVATE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: true,
      };
    }

    case ARCHIVE_BOT: {
      return {
        data: draft.data,
        id: action.id,
      };
    }
    case ARCHIVE_BOT_SUCCESS: {
      const findidx = draft.data.findIndex((x) => x._id.$oid === action.id);
      if (draft.data[findidx].status === "archived") {
        draft.data[findidx].status = "inactive";
      } else {
        draft.data[findidx].status = "archived";
      }
      return draft;
    }

    // Single bot
    case SET_BOT:
      {
        const { payload } = action;
        draft.bot = { ...draft.bot, ...payload };
      }
      return draft;

    case GET_BOT_SUCCESS: {
      draft.bot = { ...draft.bot, ...action.bots};
      return draft;
    }

    case CREATE_BOT: {
      draft.bot = action.data;
      return draft;
    }
    case CREATE_BOT_SUCCESS: {
      draft.botId = action.botId;
      return draft;
    }

    case CREATE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: false,
      };
    }

    case EDIT_BOT: {
      draft.bot = { ...draft.bot, ...action.data};
      return draft;
    }

    case EDIT_BOT_SUCCESS: {
      draft.message = action.bots.message;
      return draft;
    }

    default:
      break;
  }
}, initialState);

function symbolReducer(state = initialState, action) {
  switch (action.type) {
    case GET_SYMBOLS: {
      const newState = {
        isError: false,
        data: state.data,
      };

      return newState;
    }
    case GET_SYMBOLS_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_SYMBOLS_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
        data: action.data,
      };
    }

    default:
      return state;
  }
}

function symbolInfoReducer(state = initialState, action) {
  switch (action.type) {
    case GET_SYMBOL_INFO: {
      const newState = {
        isError: false,
        data: state.data,
      };

      return newState;
    }
    case GET_SYMBOL_INFO_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_SYMBOL_INFO_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
        data: action.data,
      };
    }

    default:
      return state;
  }
}

function candlestickReducer(state = initialState, action) {
  switch (action.type) {
    case LOAD_CANDLESTICK: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case LOAD_CANDLESTICK_SUCCESS: {
      const newState = {
        isError: false,
        data: action.payload,
      };
      return newState;
    }

    case LOAD_CANDLESTICK_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
        data: state.data,
      };
    }

    default:
      return state;
  }
}

export {
  botReducer,
  symbolInfoReducer,
  symbolReducer,
  candlestickReducer,
};
