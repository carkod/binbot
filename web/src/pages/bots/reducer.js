import {
  CREATE_BOT,
  CREATE_BOT_ERROR,
  CREATE_BOT_SUCCESS,
  DELETE_BOT,
  DELETE_BOT_ERROR,
  DELETE_BOT_SUCCESS,
  CLOSE_BOT,
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
  GET_SYMBOLS_SUCCESS,
  GET_SYMBOLS_ERROR,
  GET_SYMBOL_INFO,
  GET_SYMBOL_INFO_SUCCESS,
  GET_SYMBOL_INFO_ERROR,
  LOAD_CANDLESTICK,
  LOAD_CANDLESTICK_ERROR,
  LOAD_CANDLESTICK_SUCCESS,
  ACTIVATE_BOT,
  ACTIVATE_BOT_SUCCESS,
  ACTIVATE_BOT_ERROR,
  DEACTIVATE_BOT,
  DEACTIVATE_BOT_SUCCESS,
  DEACTIVATE_BOT_ERROR,
} from "./actions";

// The initial state of the App
export const initialState = {
  isError: false,
  data: null,
  message: null,
};

function botReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BOTS: {
      const newState = {
        ...state,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case GET_BOTS_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        data: action.bots,
      };
      return newState;
    }

    case GET_BOTS_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
      };
    }

    case CREATE_BOT: {
      const newState = {
        ...state,
        isError: false,
        data: state.data,
        botActive: false,
      };

      return newState;
    }
    case CREATE_BOT_SUCCESS: {
      const newState = {
        ...state,
        isError: false,
        botId: action.botId,
        botActive: false,
      };
      return newState;
    }

    case CREATE_BOT_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
        data: action.data,
        botActive: false,
      };
    }

    case DELETE_BOT: {
      const newState = {
        data: state.data,
        id: action.data,
      };

      return newState;
    }

    case CLOSE_BOT: {
      const newState = {
        data: state.data,
        botActive: state.botActive,
      };

      return newState;
    }

    case DELETE_BOT_SUCCESS: {
      const newState = {
        data: state.data.filter((x) => x._id.$oid !== action.removeId),
      };
      return newState;
    }

    case DELETE_BOT_ERROR: {
      return {
        ...state,
        error: action.error,
        isError: true,
        botActive: state.botActive,
      };
    }

    case ACTIVATE_BOT: {
      const newState = {
        ...state,
        isError: false,
        botActive: false,
      };

      return newState;
    }
    case ACTIVATE_BOT_SUCCESS: {
      const newState = {
        isError: false,
        data: state.data,
        message: action.message,
        botActive: true,
      };
      return newState;
    }

    case ACTIVATE_BOT_ERROR: {
      return {
        error: action.error,
        isError: true,
        data: state.data,
        botActive: false,
      };
    }

    case DEACTIVATE_BOT: {
      const newState = {
        isError: false,
        botActive: true,
      };

      return newState;
    }
    case DEACTIVATE_BOT_SUCCESS: {
      const newState = {
        isError: false,
        data: action.state,
        botActive: false,
      };
      return newState;
    }

    case DEACTIVATE_BOT_ERROR: {
      return {
        error: action.error,
        isError: true,
        data: action.state,
        botActive: true,
      };
    }

    default:
      return state;
  }
}

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
