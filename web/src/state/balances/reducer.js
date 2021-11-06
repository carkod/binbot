import {
  GET_BALANCE,
  BALANCE_SUCCESS,
  BALANCE_ERROR,
  GET_BALANCE_RAW,
  BALANCE_RAW_SUCCESS,
  BALANCE_RAW_ERROR,
  GET_ESTIMATE,
  GET_ESTIMATE_SUCCESS,
  GET_ESTIMATE_ERROR
} from "./actions";
import produce from "immer";

// The initial state of the App
export const initialState = {
  
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
      return {
        data: action.data
      };
    }

    case BALANCE_ERROR: {
      return {
        data: null,
        error: action.error
      };
    }
    default:
      return state;
  }
}


function balanceRawReducer(state = initialState, action) {
  switch (action.type) {
    case GET_BALANCE_RAW: {
      return state;
    }
    case BALANCE_RAW_SUCCESS: {
      const newState = {
        ...state,
        ...action,
      };
      return newState;
    }
    case BALANCE_RAW_ERROR: {
      return {
        ...state,
        ...action,
      };
    }
    default:
      return state;
  }
}

const estimateReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_ESTIMATE: {
      return {
        data: action.data,
      };
    }
    case GET_ESTIMATE_SUCCESS: {
      draft.data = action.data
      return draft;
    }

    case GET_ESTIMATE_ERROR: {
      return {
        error: action.error,
      };
    }

    default:
      break;
  }
}, initialState);

export {
  balanceReducer,
  balanceRawReducer,
  estimateReducer
};
