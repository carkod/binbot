import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request, { defaultOptions } from "../../request";
import {
  activateBotFailed,
  activateBotSucceeded,
  ACTIVATE_BOT,
  archiveBotFailed,
  archiveBotSucceeded,
  ARCHIVE_BOT,
  CLOSE_BOT,
  createBotFailed,
  createBotSucceeded,
  CREATE_BOT,
  deactivateBotFailed,
  deactivateBotSucceeded,
  DEACTIVATE_BOT,
  deleteBotFailed,
  deleteBotSucceeded,
  DELETE_BOT,
  editBotFailed,
  editBotSucceeded,
  EDIT_BOT,
  getBotFailed,
  getBotsFailed,
  getBotsSucceeded,
  getBotSucceeded,
  getSymbolInfoFailed,
  getSymbolInfoSucceeded,
  getSymbolsFailed,
  getSymbolsSucceeded,
  GET_BOT,
  GET_BOTS,
  GET_SYMBOLS,
  GET_SYMBOL_INFO,
  loadCandlestickFailed,
  loadCandlestickSucceeded,
  LOAD_CANDLESTICK,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getBotsApi() {
  const requestURL = process.env.REACT_APP_GET_BOTS;
  try {
    yield put(loading(true))
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getBotsSucceeded(res));
  } catch (err) {
    yield put(getBotsFailed(err));
  } finally {
    yield put(loading(false))
  }
}

export default function* watchGetBotApi() {
  yield takeLatest(GET_BOTS, getBotsApi);
}

/**
 * Get single bot
 */
export function* getBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getBotSucceeded(res));
  } catch (err) {
    yield put(getBotFailed(err));
  }
}

export function* watchGetBot() {
  yield takeLatest(GET_BOT, getBot);
}

/**
 * Create bot
 */
export function* createBotApi(body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/`;
  const options = {
    method: "POST",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(data),
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(createBotSucceeded(res));
  } catch (err) {
    yield put(createBotFailed(err));
  }
}

export function* watchCreateBot() {
  yield takeLatest(CREATE_BOT, createBotApi);
}

/**
 * Get single bot
 */
export function* editBot(payload) {
  const { data, id } = payload;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  const options = {
    method: "PUT",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(data),
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(editBotSucceeded(res));
  } catch (err) {
    yield put(editBotFailed(err));
  }
}

export function* watchEditBot() {
  yield takeLatest(EDIT_BOT, editBot);
}

/**
 * DELETE bot
 */
export function* deleteBotApi(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  const options = {
    method: "DELETE",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(deleteBotSucceeded(res));
  } catch (err) {
    yield put(deleteBotFailed(err));
  }
}

export function* watchDeleteBotApi() {
  yield takeLatest(DELETE_BOT, deleteBotApi);
}

export function* closeBotApi(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_CLOSE_BOT}/${id}`;
  const options = {
    method: "DELETE",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(deleteBotSucceeded(res));
  } catch (err) {
    yield put(deleteBotFailed(err));
  }
}

export function* watchcloseBotApi() {
  yield takeLatest(CLOSE_BOT, closeBotApi);
}

export function* getSymbols() {
  const requestURL = `${process.env.REACT_APP_NO_CANNIBALISM_SYMBOLS}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getSymbolsSucceeded(res));
  } catch (err) {
    yield put(getSymbolsFailed(err));
  }
}

export function* getSymbolInfo(payload) {
  const pair = payload.data;
  const requestURL = `${process.env.REACT_APP_SYMBOL_INFO}/${pair}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getSymbolInfoSucceeded(res));
  } catch (err) {
    yield put(getSymbolInfoFailed(err));
  }
}

/**
 * Root saga manages watcher lifecycle
 * Watches for LOAD_REPOS actions and calls getRepos when one comes in.
 * By using `takeLatest` only the result of the latest API call is applied.
 * It returns task descriptor (just like fork) so we can continue execution
 * It will be cancelled automatically on component unmount
 */
export function* watchBot() {
  yield takeLatest(GET_SYMBOL_INFO, getSymbolInfo);
  yield takeLatest(GET_SYMBOLS, getSymbols);
}

export function* activateBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_ACTIVATE_BOT}/${id}`;
  try {
    yield put(loading(true))
    const res = yield call(request, requestURL, defaultOptions);
    yield put(activateBotSucceeded(res));
  } catch (err) {
    yield put(activateBotFailed(err));
  } finally {
    yield put(loading(false))
  }
}

export function* watchActivateBot() {
  yield takeLatest(ACTIVATE_BOT, activateBot);
}

export function* deactivateBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_DEACTIVATE_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(deactivateBotSucceeded(res));
  } catch (err) {
    yield put(deactivateBotFailed(err));
  }
}

export function* watchDeactivateBot() {
  yield takeLatest(DEACTIVATE_BOT, deactivateBot);
}

/**
 * Get single bot
 */
export function* getCandlestick({ pair, interval }) {
  const requestURL = `${process.env.REACT_APP_CANDLESTICK}/${pair}/${interval}`;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(loadCandlestickSucceeded(res));
  } catch (err) {
    yield put(loadCandlestickFailed(err));
  }
}

export function* watchGetCandlestick() {
  yield takeLatest(LOAD_CANDLESTICK, getCandlestick);
}



/**
 * Archive bot
 */
 export function* archiveBotApi({ id }) {
  const requestURL = `${process.env.REACT_APP_ARCHIVE_BOT}/${id}`;
  const options = {
    method: "PUT",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", accept: "application/json" },
  };
  try {
    const res = yield call(request, requestURL, options);
    yield put(archiveBotSucceeded(res));
  } catch (err) {
    yield put(archiveBotFailed(err));
  }
}

export function* watchArchiveBot() {
  yield takeLatest(ARCHIVE_BOT, archiveBotApi);
}