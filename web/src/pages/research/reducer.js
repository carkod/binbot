import {
  GET_HISTORICAL_RESEARCH,
  GET_HISTORICAL_RESEARCH_ERROR,
  GET_HISTORICAL_RESEARCH_SUCCESS,
  GET_RESEARCH,
  GET_RESEARCH_ERROR,
  GET_RESEARCH_SUCCESS,
} from "./actions";

// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
};

function researchReducer(state = initialState, action) {
  switch (action.type) {
    case GET_RESEARCH: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case GET_RESEARCH_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_RESEARCH_ERROR: {
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

function historicalResearchReducer(state = initialState, action) {
  switch (action.type) {
    case GET_HISTORICAL_RESEARCH: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case GET_HISTORICAL_RESEARCH_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_HISTORICAL_RESEARCH_ERROR: {
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

export { researchReducer, historicalResearchReducer };
