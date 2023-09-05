import produce from "immer";

const GET_GAINERS_LOSERS = "GET_GAINERS_LOSERS";
const GET_GAINERS_LOSERS_SUCESS = "GET_GAINERS_LOSERS_SUCESS";
const GET_GAINERS_LOSERS_ERROR = "GET_GAINERS_LOSERS_ERROR";

const GET_BTC_BENCHMARK = "GET_BTC_BENCHMARK";
const GET_BTC_BENCHMARK_SUCESS = "GET_BTC_BENCHMARK_SUCESS";
const GET_BTC_BENCHMARK_ERROR = "GET_BTC_BENCHMARK_ERROR";

const GET_USDT_BENCHMARK_SUCCESS = "GET_USDT_BENCHMARK_SUCCESS";
const GET_USDT_BENCHMARK_ERROR = "GET_USDT_BENCHMARK_ERROR";
const GET_USDT_BENCHMARK = "GET_USDT_BENCHMARK";

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

/**
 * Data to compare BTC vs USDT
 */
const btcBenchmarkReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_BTC_BENCHMARK:
      return draft;

    case GET_BTC_BENCHMARK_SUCESS: {
      if (action.data) {
        action.data.btc.forEach((element, index) => {
          if (index > 0) {
            const previousQty = action.data.btc[index - 1];
            const diff = (previousQty - element) / previousQty
            draft.btcPrices.push(diff * 100);
          }
        });
        action.data.usdt.forEach((element, index) => {
          if (index > 0) {
            const previousQty = action.data.usdt[index - 1];
            const diff = (previousQty - element) / previousQty
            draft.usdtBalanceSeries.push(diff * 100);
          }
        });
        // Match dates with diff series
        action.data.dates.shift()
        draft.dates = action.data.dates;
        draft.data = action.data
      }
      return draft;
    }

    case GET_BTC_BENCHMARK_ERROR: {
      return {
        error: action.error,
      };
    }

    default:
      return draft;
  }
}, {data: null, btcPrices: [], usdtBalanceSeries: []});

export {
  gainersLosersReducer,
  btcBenchmarkReducer,
  GET_GAINERS_LOSERS,
  GET_GAINERS_LOSERS_SUCESS,
  GET_GAINERS_LOSERS_ERROR,
  GET_BTC_BENCHMARK,
  GET_BTC_BENCHMARK_SUCESS,
  GET_BTC_BENCHMARK_ERROR,
  GET_USDT_BENCHMARK_SUCCESS,
  GET_USDT_BENCHMARK_ERROR,
  GET_USDT_BENCHMARK
};
