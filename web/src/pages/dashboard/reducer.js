import produce from "immer";

const GET_GAINERS_LOSERS = "GET_GAINERS_LOSERS";
const GET_GAINERS_LOSERS_SUCESS = "GET_GAINERS_LOSERS_SUCESS";
const GET_GAINERS_LOSERS_ERROR = "GET_GAINERS_LOSERS_ERROR";

const initialState = {
  data: []
};

const gainersLosersReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_GAINERS_LOSERS:
      return draft;

    case GET_GAINERS_LOSERS_SUCESS: {
      if (action.data) {
        draft.data = action.data;
      }

      return draft;
    }

    case GET_GAINERS_LOSERS_ERROR: {
      return {
        error: action.error,
      };
    }

    default:
      return draft;
  }
}, initialState);

export {
  gainersLosersReducer,
  GET_GAINERS_LOSERS,
  GET_GAINERS_LOSERS_SUCESS,
  GET_GAINERS_LOSERS_ERROR,
};
