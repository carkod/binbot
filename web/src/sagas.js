// index.js
import watchPostRegistration from './containers/registration/saga';
import { all } from 'redux-saga/effects'
import watchPostLogin from 'containers/login/saga';

export default function* rootSaga() {
  yield all([
    watchPostRegistration(),
    watchPostLogin(),
  ])
}