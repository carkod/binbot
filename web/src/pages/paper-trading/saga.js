import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request, { buildBackUrl } from "../../request";
import { getSettingsFailed } from "../research/actions";
import {
  activateTestBotFailed,
  activateTestBotSucceeded,
  ACTIVATE_TEST_BOT,
  CLOSE_TEST_BOT,
  createTestBotFailed,
  createTestBotSucceeded,
  CREATE_TEST_BOT,
  deactivateTestBotFailed,
  deactivateTestBotSucceeded,
  DEACTIVATE_TEST_BOT,
  DELETE_TEST_BOT,
  editTestBotFailed,
  editTestBotSucceeded,
  EDIT_TEST_BOT,
  getTestBotFailed,
  getTestBotSucceeded,
  GET_TEST_BOT,
  GET_TEST_BOTS,
  getTestBotsSucceeded,
  getTestBotsFailed,
  deleteTestBotSucceeded,
  deleteTestBotFailed,
  GET_TEST_AUTOTRADE_SETTINGS,
  SAVE_TEST_AUTOTRADE_SETTINGS,
  getTestAutotradeSettingsSucceeded,
  saveTestAutotradeSettingsSucceeded,
} from "./actions";

const baseUrl = buildBackUrl();

/**
 * Bots request/response handler
 */
export function* getTestBotsApi(payload) {
  let requestURL = process.env.REACT_APP_TEST_BOT;
  if (payload.params) {
    const { startDate, endDate } = payload.params;
    const params = `${startDate ? "start_date=" + startDate + "&" : ""}${endDate ? "end_date=" + endDate : ""}`;
    requestURL += `?${params}`
  }
  try {
    yield put(loading(true));
    const res = yield call(request, requestURL);
    yield put(getTestBotsSucceeded(res));
  } catch (err) {
    yield put(getTestBotsFailed(err));
  } finally {
    yield put(loading(false));
  }
}

export default function* watchGetTestBotsApi() {
  yield takeLatest(GET_TEST_BOTS, getTestBotsApi);
}

/**
 * Get single bot
 */
export function* getTestBotApi({ id }) {
  const requestURL = `${process.env.REACT_APP_TEST_BOT}/${id}`;

  try {
    const res = yield call(request, requestURL);
    yield put(getTestBotSucceeded(res));
  } catch (err) {
    yield put(getTestBotFailed(err));
  }
}

export function* watchGetTestBotApi() {
  yield takeLatest(GET_TEST_BOT, getTestBotApi);
}

/**
 * Create bot
 */
export function* createTestBotApi({ bot }) {
  const requestURL = `${process.env.REACT_APP_TEST_BOT}`;
  try {
    const res = yield call(request, requestURL, "POST", bot);
    yield put(createTestBotSucceeded(res));
  } catch (err) {
    yield put(createTestBotFailed(err));
  }
}

export function* watchCreateTestBot() {
  yield takeLatest(CREATE_TEST_BOT, createTestBotApi);
}

/**
 * Get single bot
 */
export function* editTestBotApi({ data, id }) {
  const requestURL = `${process.env.REACT_APP_TEST_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL, "PUT", data);
    yield put(editTestBotSucceeded(res));
  } catch (err) {
    yield put(editTestBotFailed(err));
  }
}

export function* watchEditTestBotApi() {
  yield takeLatest(EDIT_TEST_BOT, editTestBotApi);
}

/**
 * DELETE bot
 */
export function* deleteTestBotApi(payload) {
  const ids = payload.removeId;
  const params = new URLSearchParams(ids.map((s) => ["id", s]));
  const requestURL = `${
    process.env.REACT_APP_TEST_BOT
  }?${params.toString()}`;
  try {
    const res = yield call(request, requestURL, "DELETE");
    yield put(deleteTestBotSucceeded(res));
  } catch (err) {
    yield put(deleteTestBotFailed(err));
  }
}

export function* watchDeleteTestbotApi() {
  yield takeLatest(DELETE_TEST_BOT, deleteTestBotApi);
}

export function* closeTestBotApi(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_DEACTIVATE_TEST_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL, "DELETE");
    yield put(deleteTestBotSucceeded(res));
  } catch (err) {
    yield put(deleteTestBotFailed(err));
  }
}

export function* watchCloseTestBotApi() {
  yield takeLatest(CLOSE_TEST_BOT, closeTestBotApi);
}

export function* activateTestBotApi(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_ACTIVATE_TEST_BOT}/${id}`;
  try {
    yield put(loading(true));
    const res = yield call(request, requestURL);
    yield put(activateTestBotSucceeded(res));
  } catch (err) {
    yield put(activateTestBotFailed(err));
  } finally {
    yield put(loading(false));
  }
}

export function* watchActivateTestBotApi() {
  yield takeLatest(ACTIVATE_TEST_BOT, activateTestBotApi);
}

export function* deactivateTestBotApi(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_DEACTIVATE_TEST_BOT}/${id}`;
  try {
    const res = yield call(request, requestURL);
    yield put(deactivateTestBotSucceeded(res));
  } catch (err) {
    yield put(deactivateTestBotFailed(err));
  }
}

export function* watchDeactivateTestBotApi() {
  yield takeLatest(DEACTIVATE_TEST_BOT, deactivateTestBotApi);
}


/**
 * Settings (controller)
 */
 export function* getTestAutotradeSettingsApi() {
  const url = new URL(process.env.REACT_APP_TEST_AUTOTRADE_SETTINGS, baseUrl)
  try {
    const res = yield call(request, url);
    yield put(getTestAutotradeSettingsSucceeded(res));
  } catch (err) {
    yield put(getSettingsFailed(err));
  }
}

export function* watchGetTestAutotradeSettingsApi() {
  yield takeLatest(GET_TEST_AUTOTRADE_SETTINGS, getTestAutotradeSettingsApi);
}


/**
 * Edit Settings (controller)
 */
 export function* editTestAutotradeSettings({ payload }) {
  const url = new URL(process.env.REACT_APP_TEST_AUTOTRADE_SETTINGS, baseUrl);
  try {
    const res = yield call(request, url, "PUT", payload);
    yield put(saveTestAutotradeSettingsSucceeded(res));
  } catch (err) {
    yield put(getSettingsFailed(err));
  }
}

export function* watchEditTestAutotradeSettings() {
  yield takeLatest(SAVE_TEST_AUTOTRADE_SETTINGS, editTestAutotradeSettings);
}
