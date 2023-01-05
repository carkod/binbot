import produce from "immer";
import {
  BALANCE_RAW_ERROR,
  BALANCE_RAW_SUCCESS,
  GET_BALANCE_RAW,
  GET_ESTIMATE,
  GET_ESTIMATE_ERROR,
  GET_ESTIMATE_SUCCESS,
} from "./actions";

// The initial state of the App
export const initialState = {
  isError: false,
  data: null,
  message: null,
};

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
      draft.data = action.data;
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

export { balanceRawReducer, estimateReducer };
