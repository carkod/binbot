import { call, put, takeLatest } from "redux-saga/effects";
import request from "../../request";
import { LOGIN, loginFailed, loginSucceeded } from "./actions";

/**
 * Login request/response handler
 */
export function* postLogin(body) {
  const { data } = body;
  const requestURL = process.env.REACT_APP_LOGIN;
  const options = {
    method: "POST",
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(data),
  };
  try {
    // Call our request helper (see 'utils/request')
    const res = yield call(request, requestURL, options);
    yield put(loginSucceeded(res));
  } catch (err) {
    yield put(loginFailed(err));
  }
}

/**
 * Root saga manages watcher lifecycle
 * Watches for LOAD_REPOS actions and calls getRepos when one comes in.
 * By using `takeLatest` only the result of the latest API call is applied.
 * It returns task descriptor (just like fork) so we can continue execution
 * It will be cancelled automatically on component unmount
 */
export default function* watchPostLogin() {
  yield takeLatest(LOGIN, postLogin);
}
