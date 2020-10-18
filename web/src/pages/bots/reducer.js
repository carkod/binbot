import { CREATE_BOT, CREATE_BOT_ERROR, CREATE_BOT_SUCCESS, DELETE_BOT, DELETE_BOT_ERROR, DELETE_BOT_SUCCESS, EDIT_BOT, EDIT_BOT_ERROR, EDIT_BOT_SUCCESS, GET_BOT, GET_BOTS, GET_BOTS_ERROR, GET_BOTS_SUCCESS, GET_BOT_ERROR, GET_BOT_SUCCESS, GET_SYMBOLS, GET_SYMBOLS_SUCCESS, GET_SYMBOLS_ERROR, GET_SYMBOL_INFO, GET_SYMBOL_INFO_SUCCESS, GET_SYMBOL_INFO_ERROR } from './actions';

// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
};

function botReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BOTS: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case GET_BOTS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.bots
      };
      return newState;
    }

    case GET_BOTS_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
      };
    }
    
    case GET_BOT: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case GET_BOT_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case GET_BOT_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
      };
    }

    case CREATE_BOT: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case CREATE_BOT_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: state.data.concat(x => x._id.$oid === action.data)
      };
      return newState;
    }

    case CREATE_BOT_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
        data: action.data
      };
    }

    case EDIT_BOT: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case EDIT_BOT_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case EDIT_BOT_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
      };
    }

    case DELETE_BOT: {
      const newState = {
        isLoading: true,
        isError: false,
        data: state.data
      };

      return newState;
    }
    case DELETE_BOT_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: state.data.filter(x => x._id.$oid !== action.data)
      };
      return newState;
    }

    case DELETE_BOT_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
      };
    }

    case GET_SYMBOLS: {
      const newState = {
        isLoading: true,
        isError: false,
        data: state.data
      };

      return newState;
    }
    case GET_SYMBOLS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case GET_SYMBOLS_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
        data: action.data
      };
    }

    default:
      return state;
  }
}


function symbolInfoReducer(state=initialState, action) {
  switch (action.type) {
    case GET_SYMBOL_INFO: {
      const newState = {
        isLoading: true,
        isError: false,
        data: state.data
      };

      return newState;
    }
    case GET_SYMBOL_INFO_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case GET_SYMBOL_INFO_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
        data: action.data
      };
    }

    default:
      return state;
  }
}

export { botReducer, symbolInfoReducer };
