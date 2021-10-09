import produce from "immer";
import {
  GET_BLACKLIST,
  GET_BLACKLIST_ERROR,
  GET_BLACKLIST_SUCCESS,
  GET_HISTORICAL_RESEARCH,
  GET_HISTORICAL_RESEARCH_ERROR,
  GET_HISTORICAL_RESEARCH_SUCCESS,
  GET_RESEARCH,
  GET_RESEARCH_ERROR,
  GET_RESEARCH_SUCCESS,
} from "./actions";

// The initial state of the App
export const initialState = {
  
  isError: false,
  data: null,
  message: null,
};

function researchReducer(state = initialState, action) {
  switch (action.type) {
    case GET_RESEARCH: {
      const newState = {
        ...state,
        data: action.data,
      };

      return newState;
    }
    case GET_RESEARCH_SUCCESS: {
      const newState = {
        ...state,
        
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_RESEARCH_ERROR: {
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

function historicalResearchReducer(state = initialState, action) {
  switch (action.type) {
    case GET_HISTORICAL_RESEARCH: {
      const newState = {
        ...state,
        data: action.data,
      };

      return newState;
    }
    case GET_HISTORICAL_RESEARCH_SUCCESS: {
      const newState = {
        ...state,
        
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_HISTORICAL_RESEARCH_ERROR: {
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

const blacklistReducer = produce((draft, action) => {
  switch (action.type) {
      case GET_BLACKLIST:
          return draft // same as just 'return'
      case GET_BLACKLIST_SUCCESS:
          // OK: we return an entirely new state
          return action.payload
      case GET_BLACKLIST_ERROR:
          // OK: the immer way
          return
      default:
        return {
          data: null,
        }
  }
})

export { researchReducer, historicalResearchReducer, blacklistReducer };
