import {
  GET_BALANCE,
  BALANCE_SUCCESS,
  BALANCE_ERROR,
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
        ...action,
      };
      return newState;
    }

    case BALANCE_ERROR: {
      return {
        ...state,
        ...action,
      };
    }
    default:
      return state;
  }
}


export {
  balanceReducer,
};
