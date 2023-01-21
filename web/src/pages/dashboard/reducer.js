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
        const filterUSDTmarket = action.data.filter(item => item.symbol.endsWith("USDT"))
        const usdtData = filterUSDTmarket.sort((a,b) => parseFloat(a.priceChangePercent) - parseFloat(b.priceChangePercent)).reverse()
        draft.data = usdtData;
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
