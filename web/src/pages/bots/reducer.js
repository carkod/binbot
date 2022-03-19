import produce from "immer";
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
  LOAD_CANDLESTICK,
  LOAD_CANDLESTICK_ERROR,
  LOAD_CANDLESTICK_SUCCESS,
} from "./actions";

// The initial state of the App
export const initialState = {
  data: null,
  message: null,
};

const botReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_BOTS: {
      return {
        data: action.data,
      };
    }
    case GET_BOTS_SUCCESS: {
      const newState = {
        data: action.bots,
      };
      return newState;
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
      draft.removeId = action.removeId
      return draft;
    }

    case CLOSE_BOT: {
      const newState = {
        data: draft.data,
        botActive: draft.botActive,
      };

      return newState;
    }

    case DELETE_BOT_SUCCESS: {
      return draft;
    }

    case DELETE_BOT_ERROR: {
      return {
        error: action.error,
        botActive: draft.botActive,
      };
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
      const findidx = draft.data.findIndex(x => x._id.$oid === action.id);
      draft.data[findidx].status = "inactive"
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
      const findidx = draft.data.findIndex(x => x._id.$oid === action.id);
      if (draft.data[findidx].status === "archived") {
        draft.data[findidx].status = "inactive"  
      } else {
        draft.data[findidx].status = "archived"
      }
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
