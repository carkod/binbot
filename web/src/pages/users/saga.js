import { call, put, takeLatest } from "redux-saga/effects";
import { loading } from "../../containers/spinner/actions";
import request, { defaultOptions } from "../../request";
import {
  deleteUserFailed,
  deleteUserSucceeded,
  DELETE_USER,
  editUserFailed,
  editUserSucceded,
  EDIT_USER,
  getUsersFailed,
  getUsersSucceded,
  GET_USERS,
  registerUserFailed,
  registerUserSucceeded,
  REGISTER_USER,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getUsersApi() {
  const requestURL = process.env.REACT_APP_USERS;
  try {
    yield put(loading(true));
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getUsersSucceded(res));
  } catch (err) {
    yield put(getUsersFailed(err));
  } finally {
    yield put(loading(false));
  }
}

export default function* watchUsersApi() {
  yield takeLatest(GET_USERS, getUsersApi);
}

/**
 * Get single bot
 */
export function* editUserApi({ data, id }) {
  const requestURL = `${process.env.REACT_APP_USERS}/${id}`;
  let options = defaultOptions;
  options.method = "PUT";
  options.body = JSON.stringify(data);
  try {
    const res = yield call(request, requestURL, options);
    yield put(editUserSucceded(res));
  } catch (err) {
    yield put(editUserFailed(err));
  }
}

export function* watchEditUserApi() {
  yield takeLatest(EDIT_USER, editUserApi);
}

/**
 * DELETE bot
 */
export function* deleteUserApi({ id }) {
  const requestURL = `${process.env.REACT_APP_USERS}/${id}`;
  let options = defaultOptions;
  options.method = "DELETE";
  try {
    const res = yield call(request, requestURL, options);
    yield put(deleteUserSucceeded(res));
  } catch (err) {
    yield put(deleteUserFailed(err));
  }
}

export function* watchDeleteUserApi() {
  yield takeLatest(DELETE_USER, deleteUserApi);
}

export function* createUserApi({ data }) {
  const requestURL = `${process.env.REACT_APP_REGISTER_USER}`;
  let options = defaultOptions;
  options.method = "POST";
  options.body = JSON.stringify(data);
  try {
    const res = yield call(request, requestURL, options);
    yield put(registerUserSucceeded(res));
  } catch (err) {
    yield put(registerUserFailed(err));
  }
}

export function* watchCreateUserApi() {
  yield takeLatest(REGISTER_USER, createUserApi);
}
