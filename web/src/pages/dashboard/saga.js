import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { balanceFailed, balanceSucceeded, getAssetsFailed, getAssetsSucceeded, GET_ASSETS, GET_BALANCE, updateAssetsFailed, updateAssetsSucceeded, UPDATE_ASSETS } from './actions';

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
 * /account/update-balance
 */
export function* updateAssetsValue() {
  const requestURL = process.env.REACT_APP_ASSETS_UPDATE;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(updateAssetsSucceeded(res));
  } catch (err) {
    yield put(updateAssetsFailed(err));
  }
}

export function* watchUpdateAssets() {
  yield takeLatest(UPDATE_ASSETS, updateAssetsValue);
}