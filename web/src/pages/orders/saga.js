import { call, put, takeLatest } from "redux-saga/effects";
import request from "../../request";
import {
  deleteOpenOrdersFailed,
  deleteOpenOrdersSucceeded,
  DELETE_OPEN_ORDERS,
  getOpenOrdersFailed,
  getOpenOrdersSucceeded,
  getOrdersFailed,
  getOrdersSucceeded,
  GET_ALL_ORDERS,
  GET_OPEN_ORDERS,
  POLL_ORDERS,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getAllOrders(payload) {
  const { limit, offset, status } = payload.data;
  const requestURL = `${process.env.REACT_APP_ALL_ORDERS}?limit=${limit}&offset=${offset}&status=${status}`;
  const options = {
    method: "GET",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(getOrdersSucceeded(res));
  } catch (err) {
    yield put(getOrdersFailed(err));
  }
}

export function* watchGetOrders() {
  yield takeLatest(GET_ALL_ORDERS, getAllOrders);
}

/**
 * Open orders
 */
export function* getAllOpenOrders() {
  const requestURL = `${process.env.REACT_APP_OPEN_ORDERS}`;
  const options = {
    method: "GET",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
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

export function* deleteOpenOrders(payload) {
  const { symbol, orderId } = payload.data;
  const requestURL = `${process.env.REACT_APP_OPEN_ORDERS}/${symbol}/${orderId}`;
  const options = {
    method: "DELETE",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(deleteOpenOrdersSucceeded(res));
  } catch (err) {
    yield put(deleteOpenOrdersFailed(err));
  }
}

export function* watchDeleteOpenOrders() {
  yield takeLatest(DELETE_OPEN_ORDERS, deleteOpenOrders);
}

/**
 * Create bot
 */
export function* pollOrders() {
  const requestURL = `${process.env.REACT_APP_POLL}`;
  const options = {
    method: "GET",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", accept: "application/json" },
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(pollOrders(res));
  } catch (err) {
    // yield put(createBotFailed(err));
  }
}

export function* watchPollOrders() {
  yield takeLatest(POLL_ORDERS, pollOrders);
}
