import { call, put, takeLatest } from "redux-saga/effects";
import request from "../../request";
import {
  registerUserFailed,
  registerUserSucceded,
  REGISTER_USER,
} from "./actions";

/**
 * Github repos request/response handler
 */
export function* postRegistration(body) {
  const { data } = body;
  const requestURL = process.env.REACT_APP_REGISTRATION;
  try {
    yield call(request, requestURL, {
      method: "POST",
      body: JSON.stringify(data),
    });
    yield put(registerUserSucceded(body));
  } catch (err) {
    yield put(registerUserFailed(err));
  }
}

/**
 * Root saga manages watcher lifecycle
 */
export default function* watchPostRegistration() {
  // Watches for LOAD_REPOS actions and calls getRepos when one comes in.
  // By using `takeLatest` only the result of the latest API call is applied.
  // It returns task descriptor (just like fork) so we can continue execution
  // It will be cancelled automatically on component unmount
  yield takeLatest(REGISTER_USER, postRegistration);
}
