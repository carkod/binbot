import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request from "../../request";
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
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getTestBotsApi() {
  const requestURL = process.env.REACT_APP_TEST_BOT;
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
export function* createTestBotApi(body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_TEST_BOT}`;
  try {
    const res = yield call(request, requestURL, "POST", data);
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
export function* editTestBotApi(payload) {
  const { data, id } = payload;
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
export function* deleteBotApi(payload) {
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

export function* watchDeleteBotApi() {
  yield takeLatest(DELETE_TEST_BOT, deleteBotApi);
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
