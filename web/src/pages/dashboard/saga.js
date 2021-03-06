import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { balanceFailed, balanceSucceeded, BALANCE_DIFF, getAssetsFailed, getAssetsSucceeded, getBalanceDiffFailed, getBalanceDiffSucceeded, getBalanceInBtcFailed, getBalanceInBtcSucceeded, GET_ASSETS, GET_BALANCE, GET_BALANCE_IN_BTC } from './actions';

/**
 * Account request/response handler
 */
export function* getBalanceAll() {
  const requestURL = process.env.REACT_APP_ACCOUNT_BALANCE_ALL;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(balanceSucceeded(res));
  } catch (err) {
    yield put(balanceFailed(err));
  }
}

export function* watchGetBalanceAll() {
  yield takeLatest(GET_BALANCE, getBalanceAll);
}

/**
 * Portolio of assets balance
 * /account/assets
 * Assets model
 */
export function* getAssetsValue() {
  const requestURL = process.env.REACT_APP_ASSETS;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getAssetsSucceeded(res));
  } catch (err) {
    yield put(getAssetsFailed(err));
  }
}

export function* watchAssetsValue() {
  yield takeLatest(GET_ASSETS, getAssetsValue);
}

/**
 * Update Portolio of assets balance
 * /account/ticker23/<symbol>
 */
export function* getBalanceDiffApi({days}) {
  const requestURL = `${process.env.REACT_APP_BALANCE_DIFF}?days=${days}`;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getBalanceDiffSucceeded(res));
  } catch (err) {
    yield put(getBalanceDiffFailed(err));
  }
}

export function* watchGetBalanceDiff() {
  yield takeLatest(BALANCE_DIFF, getBalanceDiffApi);
}


/**
 * Account request/response handler
 */
export function* getBalanceInBtcApi() {
  const requestURL = process.env.REACT_APP_ACCOUNT_BALANCE_BTC;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getBalanceInBtcSucceeded(res));
  } catch (err) {
    yield put(getBalanceInBtcFailed(err));
  }
}

export function* watchGetBalanceInBtc() {
  yield takeLatest(GET_BALANCE_IN_BTC, getBalanceInBtcApi);
}
