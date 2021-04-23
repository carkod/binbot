import {
  GET_BALANCE,
  BALANCE_SUCCESS,
  BALANCE_ERROR,
  GET_ASSETS,
  GET_ASSETS_SUCCESS,
  GET_ASSETS_ERROR,
  UPDATE_ASSETS,
  UPDATE_ASSETS_SUCCESS,
  UPDATE_ASSETS_ERROR,
  BALANCE_DIFF,
  BALANCE_DIFF_SUCCESS,
  BALANCE_DIFF_ERROR,
  GET_BALANCE_IN_BTC,
  GET_BALANCE_IN_BTC_SUCCESS,
  GET_BALANCE_IN_BTC_ERROR,
} from "./actions";

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
      return state;
    }
    case BALANCE_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
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
        data: action.data,
      };

      return newState;
    }
    case GET_ASSETS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
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

    case UPDATE_ASSETS: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
      };

      return newState;
    }
    case UPDATE_ASSETS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
      };
      return newState;
    }

    case UPDATE_ASSETS_ERROR: {
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

function balanceDiffReducer(state = initialState, action) {
  switch (action.type) {
    case BALANCE_DIFF: {
      return state;
    }
    case BALANCE_DIFF_SUCCESS: {
      const newState = {
        ...state,
        data: action.data,
      };
      return newState;
    }

    case BALANCE_DIFF_ERROR: {
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

function balanceInBtcReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BALANCE_IN_BTC: {
      return state;
    }
    case GET_BALANCE_IN_BTC_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_BALANCE_IN_BTC_ERROR: {
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

export {
  balanceReducer,
  assetsReducer,
  balanceDiffReducer,
  balanceInBtcReducer,
};
