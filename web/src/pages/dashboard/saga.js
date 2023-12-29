import { call, put, takeLatest } from "redux-saga/effects";
import request from "../../request";
import {
  GET_GAINERS_LOSERS,
  GET_GAINERS_LOSERS_SUCESS,
  GET_GAINERS_LOSERS_ERROR,
  GET_BTC_BENCHMARK,
  GET_BTC_BENCHMARK_SUCESS,
  GET_BTC_BENCHMARK_ERROR,
  GET_USDT_BENCHMARK,
  GET_GAINERS_LOSERS_SERIES,
  GET_GAINERS_LOSERS_SERIES_SUCCESS,
  GET_GAINERS_LOSERS_SERIES_ERROR,
} from "./reducer";
import { addNotification } from "../../validations";

export function getGainersLosers() {
  return {
    type: GET_GAINERS_LOSERS,
  };
}

function getGainersLosersSucceeded(res) {
  return {
    type: GET_GAINERS_LOSERS_SUCESS,
    data: res,
  };
}

function getGainersLosersFailed(err) {
  return {
    type: GET_GAINERS_LOSERS_ERROR,
  };
}

export function getGainersLosersSeries() {
  return {
    type: GET_GAINERS_LOSERS_SERIES,
  };
}

function getGainersLosersSeriesSucceeded(res) {
  return {
    type: GET_GAINERS_LOSERS_SERIES_SUCCESS,
    data: res.data,
  };
}

function getGainersLosersSeriesFailed(err) {
  return {
    type: GET_GAINERS_LOSERS_SERIES_ERROR,
  };
}

/**
 * Get raw list 24hour ticker
 * of gainers and losers
 */
export function* getGainersLosersApi() {
  const requestURL = `${process.env.REACT_APP_TICKER_24}`;
  try {
    const res = yield call(request, requestURL, "GET");
    yield put(getGainersLosersSucceeded(res));
  } catch (err) {
    yield put(getGainersLosersFailed(err));
  }
}
export function* watchGetGainersLosers() {
  yield takeLatest(GET_GAINERS_LOSERS, getGainersLosersApi);
}

export function* getGainersLosersSeriesApi() {
  const requestURL = `${process.env.REACT_APP_GAINERS_LOSERS_SERIES}?size=7`;
  try {
    const res = yield call(request, requestURL, "GET");
    yield put(getGainersLosersSeriesSucceeded(res));
  } catch (err) {
    yield put(getGainersLosersSeriesFailed(err));
  }
}
export function* watchGetGainersLosersSeries() {
  yield takeLatest(GET_GAINERS_LOSERS_SERIES, getGainersLosersSeriesApi);
}

export function getBenchmarkData() {
  return {
    type: GET_BTC_BENCHMARK,
  };
}

function getBenchmarkDataSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: GET_BTC_BENCHMARK_SUCESS,
    data: res.data,
  };
}

function getBenchmarkDataFailed(err) {
  addNotification("FAILED!", err.message, "error");
  return {
    type: GET_BTC_BENCHMARK_ERROR,
  };
}

export function getBenchmarkUsdt(err) {
  return {
    type: GET_USDT_BENCHMARK,
  };
}

/**
 * Get binance rollowing window data
 * https://binance-docs.github.io/apidocs/spot/en/#rolling-window-price-change-statistics
 */
export function* getBenchmarksApi() {
  const requestURL = `${process.env.REACT_APP_BALANCE_SERIES}`;
  try {
    const res = yield call(request, requestURL, "GET");
    yield put(getBenchmarkDataSucceeded(res));
  } catch (err) {
    yield put(getBenchmarkDataFailed(err));
  }
}

export function* watchBenchmarksApi() {
  yield takeLatest(GET_BTC_BENCHMARK, getBenchmarksApi);
}
