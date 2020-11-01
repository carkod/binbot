import { GET_BALANCE, BALANCE_SUCCESS, BALANCE_ERROR, GET_ASSETS, GET_ASSETS_SUCCESS, GET_ASSETS_ERROR } from './actions';

// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
};

function balanceReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BALANCE: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case BALANCE_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case BALANCE_ERROR: {
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

function assetsReducer(state = initialState, action) {
  switch (action.type) {
    case GET_ASSETS: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case GET_ASSETS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data
      };
      return newState;
    }

    case GET_ASSETS_ERROR: {
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

export { balanceReducer, assetsReducer };
