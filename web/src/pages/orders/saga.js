import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { getOpenOrdersFailed, getOpenOrdersSucceeded, getOrdersFailed, getOrdersSucceeded, GET_ALL_ORDERS, GET_OPEN_ORDERS } from './actions';

/**
 * Bots request/response handler
 */
export function* getAllOrders(payload) {
  const { limit, offset } = payload.data;
  const requestURL = `${process.env.REACT_APP_ALL_ORDERS}?limit=${limit}&offset=${offset}`;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getOrdersSucceeded(res));
  } catch (err) {
    yield put(getOrdersFailed(err));
  }
}

export function* watchGetOrders() {
  yield takeLatest(GET_ALL_ORDERS, getAllOrders)
}

/**
 * Get single bot
 */
export function* getAllOpenOrders(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_OPEN_ORDERS}/${id}`;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getOpenOrdersSucceeded(res));
  } catch (err) {
    yield put(getOpenOrdersFailed(err));
  }
}

export function* watchOpenOrders() {
  yield takeLatest(GET_OPEN_ORDERS, getAllOpenOrders);
}

/**
 * Create bot
 */
export function* pollOrders(body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_POLL}/`;
  const options = {
    method: 'POST',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", "accept": "application/json" },
    body: JSON.stringify(data)
  }
  try {
    yield call(request, requestURL, options);
    // yield put(pollOrders(res));
  } catch (err) {
    // yield put(createBotFailed(err));
  }
}
