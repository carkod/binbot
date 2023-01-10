import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request from "../../request";
import {
  balanceRawFailed,
  balanceRawSucceeded,
  getEstimateFailed,
  getEstimateSucceeded,
  GET_BALANCE_RAW,
  GET_ESTIMATE,
} from "./actions";

/**
 * Account request/response handler
 */
export function* getRawBalanceApi() {
  const requestURL = `${process.env.REACT_APP_ACCOUNT_BALANCE_RAW}`;
  try {
    const res = yield call(request, requestURL);
    yield put(balanceRawSucceeded(res));
  } catch (err) {
    yield put(balanceRawFailed(err));
  } finally {
    yield put(loading(false));
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
    const res = yield call(request, requestURL);
    yield put(getEstimateSucceeded(res));
  } catch (err) {
    yield put(getEstimateFailed(err));
  } finally {
    yield put(loading(false));
  }
}

export function* watchGetEstimate() {
  yield takeLatest(GET_ESTIMATE, getEstimateApi);
}
