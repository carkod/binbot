import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request, { getToken } from "../../request";
import {
  balanceFailed,
  balanceRawFailed,
  balanceRawSucceeded,
  balanceSucceeded, getEstimateFailed, getEstimateSucceeded, GET_BALANCE, GET_BALANCE_RAW, GET_ESTIMATE
} from "./actions";

const defaultOptions = {
  method: "GET",
  mode: "cors", // no-cors, *cors, same-origin
  cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  headers: {
    "Authorization": `Bearer ${getToken()}`
  }
}

/**
 * Account request/response handler
 */
export function* getBalanceApi() {
  const requestURL = process.env.REACT_APP_ACCOUNT_BALANCE;
  try {
    yield put(loading(true))
    const res = yield call(request, requestURL, defaultOptions);
    yield put(balanceSucceeded(res));
  } catch (err) {
    yield put(balanceFailed(err));
  } finally {
    yield put(loading(false))
  }
}

export function* watchGetBalanceApi() {
  yield takeLatest(GET_BALANCE, getBalanceApi);
}


/**
 * Account request/response handler
 */
 export function* getRawBalanceApi() {
  const requestURL = `${process.env.REACT_APP_ACCOUNT_BALANCE_RAW}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(balanceRawSucceeded(res));
  } catch (err) {
    yield put(balanceRawFailed(err));
  } finally {
    yield put(loading(false))
  }
}

export function* watchRawBalance() {
  yield takeLatest(GET_BALANCE_RAW, getRawBalanceApi);
}

/**
 * Account request/response handler
 */
 export function* getEstimateApi() {
  const requestURL = `${process.env.REACT_APP_BALANCE_ESTIMATE}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getEstimateSucceeded(res));
  } catch (err) {
    yield put(getEstimateFailed(err));
  } finally {
    yield put(loading(false))
  }
}

export function* watchGetEstimate() {
  yield takeLatest(GET_ESTIMATE, getEstimateApi);
}
