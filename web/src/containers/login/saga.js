import { call, put, takeLatest } from "redux-saga/effects";
import { requestForm } from "../../request";
import { LOGIN, loginFailed, loginSucceeded } from "./actions";

/**
 * Login request/response handler
 */
export function* postLogin(body) {
  const { data } = body;
  const requestURL = `${process.env.REACT_APP_LOGIN}`;

  const formData = new FormData();
  formData.append("username", data.email)
  formData.append("password", data.password)

  try {
    const res = yield call(requestForm, requestURL, "POST", formData);
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
