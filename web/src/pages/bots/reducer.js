import produce from "immer";
import {
  bot,
  computeTotalProfit
} from "../../state/bots/actions";
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
  EDIT_BOT_ERROR,
  EDIT_BOT_SUCCESS,
  GET_BOT,
  GET_BOTS,
  GET_BOTS_ERROR,
  GET_BOTS_SUCCESS,
  GET_BOT_ERROR,
  GET_BOT_SUCCESS,
  GET_SYMBOLS,
  GET_SYMBOLS_ERROR,
  GET_SYMBOLS_SUCCESS,
  GET_SYMBOL_INFO,
  GET_SYMBOL_INFO_ERROR,
  GET_SYMBOL_INFO_SUCCESS,
  loadCandlestick,
  LOAD_CANDLESTICK,
  LOAD_CANDLESTICK_ERROR,
  LOAD_CANDLESTICK_SUCCESS,
  SET_BOT
} from "./actions";
import { getQuoteAsset } from "./requests";

// The initial state of the App
export const initialState = {
  bot: bot,
  data: null,
  message: null,
  params: {
    startDate: null,
    endDate: null,
  },
};


computeAvailableBalance = (draft) => {
  /**
   * Refer to bots.md
   */
  const { base_order_size, safety_orders, short_order, quoteAsset, orders } = draft.bot;
  const { balances } = this.props;

  let value = "0";
  let name = "";
  if (!checkValue(quoteAsset) && !checkValue(balances)) {
    balances.forEach((x) => {
      if (quoteAsset === x.asset) {
        value = x.free;
        name = x.asset;
      }
    });

    if (
      !checkValue(value) &&
      !checkBalance(value) &&
      Object.values(safety_orders).length > 0 &&
      this.props.bot
    ) {
      const baseOrder = parseFloat(base_order_size) * 1; // base order * 100% of all balance
      const safetyOrders = Object.values(safety_orders).reduce(
        (v, a) => {
          return parseFloat(v.so_size) + parseFloat(a.so_size);
        },
        { so_size: 0 }
      );
      const shortOrder = parseFloat(short_order);
      const checkBaseOrder = orders.find(
        (x) => x.deal_type === "base_order"
      );
      let updatedValue = value - (baseOrder + safetyOrders + shortOrder);
      if (!checkValue(checkBaseOrder) && "deal_type" in checkBaseOrder) {
        updatedValue = baseOrder + updatedValue;
      }
      updatedValue.toFixed(8);

      // Check that we have enough funds
      // If not return error
      if (parseFloat(updatedValue) > 0) {
        draft.bot.balance_available = updatedValue;
        draft.bot.balance_available_asset = name;
        draft.bot.baseOrderSizeError = false;
        draft.bot.balanceAvailableError = false;

      } else {
        draft.bot.baseOrderSizeError = true;
        draft.bot.formIsValid = false;
      }
    } else {
      draft.bot.balance_available = value;
      draft.bot.balance_available_asset = name;
      draft.bot.balanceAvailableError = true;
      draft.bot.formIsValid = false;
    }
  }
};

const pairUpdate = async (pair, draft) => {
  /**
   * Every time the pair updates do:
   * 1. Update quoteAsset
   * 2. Update candlesticks
   * 3. Compute available balance
   */
  const quoteAsset = getQuoteAsset(pair);
  draft.bot.quoteAsset = quoteAsset;
  
  loadCandlestick(pair, draft.bot.candlestick_interval, draft.bot.deal.buy_timestamp)


}

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

    case CREATE_BOT: {
      const newState = {
        data: draft.data,
        botActive: false,
      };

      return newState;
    }
    case CREATE_BOT_SUCCESS: {
      const newState = {
        botId: action.botId,
        botActive: false,
        data: draft.data,
      };
      return newState;
    }

    case CREATE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: false,
      };
    }

    case DELETE_BOT: {
      draft.removeId = action.removeId;
      return draft;
    }

    case DELETE_BOT_SUCCESS:
      draft.bots = draft.bots.filter(
        (x) => !x._id.$oid.includes(draft.removeId)
      );
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
      const newState = {
        isError: false,
        botActive: false,
        data: draft.data,
      };

      return newState;
    }
    case ACTIVATE_BOT_SUCCESS: {
      const newState = {
        data: draft.data,
        message: action.message,
        botActive: true,
      };
      return newState;
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
    case SET_BOT: {
      const { payload } = action;
      if ("pair" in payload) {
        pairUpdate(payload.pair)
      }
      draft.bot = { ...draft.bot, ...payload };
    }
    return draft;

    case GET_BOT_SUCCESS: {
      draft.bot = action.data
      draft.data = action.bots
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

function getSingleBotReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BOT: {
      const newState = {
        ...state,
        isError: false,
        data: state.data,
      };

      return newState;
    }
    case GET_BOT_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        data: action.bots,
        message: action.message,
      };
      return newState;
    }

    case GET_BOT_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
      };
    }

    default:
      return state;
  }
}

function editBotReducer(state = initialState, action) {
  switch (action.type) {
    case EDIT_BOT: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case EDIT_BOT_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case EDIT_BOT_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
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
  getSingleBotReducer,
  editBotReducer,
  candlestickReducer,
};
