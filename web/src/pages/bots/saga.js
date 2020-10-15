import { call, put, takeLatest } from 'redux-saga/effects';
import request from '../../request';
import { getBotsSucceeded, getBotsFailed, deleteBotFailed, deleteBotSucceeded, editBotSucceeded, editBotFailed, createBotSucceeded, createBotFailed, getBotSucceeded, getBotFailed, GET_BOT, CREATE_BOT, EDIT_BOT, DELETE_BOT, GET_BOTS } from './actions';

/**
 * Bots request/response handler
 */
export function* getBots() {
  const requestURL = process.env.REACT_APP_GET_BOTS;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getBotsSucceeded(res));
  } catch (err) {
    yield put(getBotsFailed(err));
  }
}

/**
 * Get single bot
 */
export function* getBot(id) {
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  const options = {
    method: 'GET',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(getBotSucceeded(res));
  } catch (err) {
    yield put(getBotFailed(err));
  }
}

/**
 * Create bot
 */
export function* createBot(body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}`;
  const options = {
    method: 'POST',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
    body: JSON.stringify(data)
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(createBotSucceeded(res));
  } catch (err) {
    yield put(createBotFailed(err));
  }
}


/**
 * Get single bot
 */
export function* editBot(id, body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  const options = {
    method: 'PUT',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
    body: JSON.stringify(data)
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(editBotSucceeded(res));
  } catch (err) {
    yield put(editBotFailed(err));
  }
}

/**
 * Get single bot
 */
export function* deleteBot(payload) {
  const id = payload.data;
  const requestURL = `${process.env.REACT_APP_GET_BOTS}/${id}`;
  const options = {
    method: 'DELETE',
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
  }
  try {
    const res = yield call(request, requestURL, options);
    yield put(deleteBotSucceeded(res));
  } catch (err) {
    yield put(deleteBotFailed(err));
  }
}


/**
 * Root saga manages watcher lifecycle
 * Watches for LOAD_REPOS actions and calls getRepos when one comes in.
 * By using `takeLatest` only the result of the latest API call is applied.
 * It returns task descriptor (just like fork) so we can continue execution
 * It will be cancelled automatically on component unmount
 */
export default function* watchBot() {
  yield takeLatest(GET_BOT, getBot);
  yield takeLatest(GET_BOTS, getBots);
  yield takeLatest(CREATE_BOT, createBot);
  yield takeLatest(EDIT_BOT, editBot);
  yield takeLatest(DELETE_BOT, deleteBot);
}
