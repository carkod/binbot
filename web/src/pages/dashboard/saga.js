import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { balanceFailed, balanceSucceeded, BALANCE_DIFF, getAssetsFailed, getAssetsSucceeded, getBalanceDiffFailed, getBalanceDiffSucceeded, GET_ASSETS, GET_BALANCE } from './actions';

/**
 * Account request/response handler
 */
export function* getAccount() {
  const requestURL = process.env.REACT_APP_ACCOUNT;
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

export default function* watchGetAccount() {
  yield takeLatest(GET_BALANCE, getAccount);
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