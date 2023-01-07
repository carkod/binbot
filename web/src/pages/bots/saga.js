import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request, { buildBackUrl } from "../../request";
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
  editSettingsFailed,
  editSettingsSucceeded,
  EDIT_BOT,
  EDIT_SETTINGS,
  getBotFailed,
  getBotsFailed,
  getBotsSucceeded,
  getBotSucceeded,
  getSettingsFailed,
  getSettingsSucceeded,
  getSymbolInfoFailed,
  getSymbolInfoSucceeded,
  getSymbolsFailed,
  getSymbolsSucceeded,
  GET_BOT,
  GET_BOTS,
  GET_SETTINGS,
  GET_SYMBOLS,
  GET_SYMBOL_INFO,
  loadCandlestickFailed,
  loadCandlestickSucceeded,
  LOAD_CANDLESTICK,
} from "./actions";

const baseUrl = buildBackUrl();

/**
 * Bots request/response handler
 */
export function* getBotsApi(payload) {
  let requestURL = `${process.env.REACT_APP_GET_BOTS}`;
  if (payload.params) {
    const { startDate, endDate, status=null } = payload.params;
    const params = `${startDate ? "start_date=" + startDate + "&" : ""}${endDate ? "end_date=" + endDate : ""}${status ? "status=" + status : ""}`;
    requestURL += `?${params}`
  }

  try {
    yield put(loading(true));
    const res = yield call(request, requestURL);
    yield put(getBotsSucceeded(res));
  } catch (err) {
    yield put(getBotsFailed(err));
  } finally {
    yield put(loading(false));
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
    const res = yield call(request, requestURL);
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
  const requestURL = `${process.env.REACT_APP_GET_BOTS}`;
  try {
    const res = yield call(request, requestURL, "POST", data);
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
export function* editBot({ data, id }) {
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  try {
    const res = yield call(request, requestURL, "PUT", data);
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
  const ids = payload.removeId;
  const params = new URLSearchParams(ids.map(s=>['id',s]))
  const requestURL = `${process.env.REACT_APP_GET_BOTS}?${params.toString()}`;
  try {
    const res = yield call(request, requestURL, "DELETE");
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
  const requestURL = `${process.env.REACT_APP_DEACTIVATE_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL, "DELETE");
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
    const res = yield call(request, requestURL);
    yield put(getSymbolsSucceeded(res));
  } catch (err) {
    yield put(getSymbolsFailed(err));
  }
}

export function* getSymbolInfoApi(payload) {
  const pair = payload.data;
  const requestURL = `${process.env.REACT_APP_SYMBOL_INFO}/${pair}`;
  try {
    const res = yield call(request, requestURL);
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
  yield takeLatest(GET_SYMBOL_INFO, getSymbolInfoApi);
  yield takeLatest(GET_SYMBOLS, getSymbols);
}

export function* activateBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_ACTIVATE_BOT}/${id}`;
  try {
    yield put(loading(true));
    const res = yield call(request, requestURL);
    yield put(activateBotSucceeded(res));
  } catch (err) {
    yield put(activateBotFailed(err));
  } finally {
    yield put(loading(false));
  }
}

export function* watchActivateBot() {
  yield takeLatest(ACTIVATE_BOT, activateBot);
}

export function* deactivateBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_DEACTIVATE_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL);
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
export function* getCandlestick({ pair, interval, start_time = null }) {
  const requestURL = `${process.env.REACT_APP_CANDLESTICK}?symbol=${pair}&interval=${interval}`;
  try {
    const res = yield call(request, requestURL);
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
  try {
    const res = yield call(request, requestURL, "PUT");
    yield put(archiveBotSucceeded(res));
  } catch (err) {
    yield put(archiveBotFailed(err));
  }
}

export function* watchArchiveBot() {
  yield takeLatest(ARCHIVE_BOT, archiveBotApi);
}

/**
 * Settings (controller)
 */
 export function* getSettingsApi() {
  const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER, baseUrl)
  try {
    const res = yield call(request, url);
    yield put(getSettingsSucceeded(res));
  } catch (err) {
    yield put(getSettingsFailed(err));
  }
}

export function* watchGetSettingsApi() {
  yield takeLatest(GET_SETTINGS, getSettingsApi);
}


/**
 * Edit Settings (controller)
 */
 export function* editSettingsApi({ data }) {
  const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER, baseUrl);
  try {
    const res = yield call(request, url, "PUT", data);
    yield put(editSettingsSucceeded(res));
  } catch (err) {
    yield put(editSettingsFailed(err));
  }
}

export function* watchEditSettingsApi() {
  yield takeLatest(EDIT_SETTINGS, editSettingsApi);
}
