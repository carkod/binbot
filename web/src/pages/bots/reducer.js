import { CREATE_BOT, CREATE_BOT_ERROR, CREATE_BOT_SUCCESS, DELETE_BOT, DELETE_BOT_ERROR, DELETE_BOT_SUCCESS, EDIT_BOT, EDIT_BOT_ERROR, EDIT_BOT_SUCCESS, GET_BOT, GET_BOTS, GET_BOTS_ERROR, GET_BOTS_SUCCESS, GET_BOT_ERROR, GET_BOT_SUCCESS } from './actions';

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
        data: action.data
      };
      return newState;
    }

    case CREATE_BOT_ERROR: {
      return { 
        ...state, 
        error: action.error, 
        isLoading: false, 
        isError: true,
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
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case DELETE_BOT_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
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
    default:
      return state;
  }
}

export default botReducer;
