import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request from "../../request";
import {
  balanceFailed,
  balanceRawFailed,
  balanceRawSucceeded,
  balanceSucceeded, GET_BALANCE, GET_BALANCE_RAW
} from "./actions";

const defaultOptions = {
  method: "GET",
  mode: "cors", // no-cors, *cors, same-origin
  cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
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
