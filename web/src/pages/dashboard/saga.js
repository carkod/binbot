import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { balanceFailed, balanceSucceeded, GET_BALANCE } from './actions';

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

/**
 * Root saga manages watcher lifecycle
 * Watches for LOAD_REPOS actions and calls getRepos when one comes in.
 * By using `takeLatest` only the result of the latest API call is applied.
 * It returns task descriptor (just like fork) so we can continue execution
 * It will be cancelled automatically on component unmount
 */
export default function* watchGetAccount() {
  yield takeLatest(GET_BALANCE, getAccount);
}
