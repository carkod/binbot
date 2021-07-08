import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request from "../../request";
import {
  balanceFailed,
  balanceSucceeded, GET_BALANCE
} from "./actions";

/**
 * Account request/response handler
 */
export function* getBalanceApi() {
  const requestURL = process.env.REACT_APP_ACCOUNT_BALANCE;
  const options = {
    method: "GET",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
  try {
    yield put(loading(true))
    const res = yield call(request, requestURL, options);
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
