import { call, put, takeLatest } from 'redux-saga/effects';
import request, { setToken } from '../request';
import { loginFailed, loginSucceeded, LOGIN } from './actions';


const host = 'http://localhost:5000/';

/**
 * Github repos request/response handler
 */
export function* postLogin(body) {
  const { data } = body;
  const requestURL = `${host}user/login`;
  try {
    // Call our request helper (see 'utils/request')
    const res = yield call(request, requestURL, { method: 'POST', body: JSON.stringify(data)});
    setToken(res.access_token)
    yield put(loginSucceeded(res));
  } catch (err) {
    yield put(loginFailed(err));
  }
}

/**
 * Root saga manages watcher lifecycle
 */
export default function* watchPostLogin() {
  // Watches for LOAD_REPOS actions and calls getRepos when one comes in.
  // By using `takeLatest` only the result of the latest API call is applied.
  // It returns task descriptor (just like fork) so we can continue execution
  // It will be cancelled automatically on component unmount
  yield takeLatest(LOGIN, postLogin);
}
