// index.js
import { all } from 'redux-saga/effects'
import watchPostRegistration from './containers/registration/saga';
import watchPostLogin from 'containers/login/saga';
import watchGetAccount from 'pages/dashboard/saga';
import watchBot, { watchCreateBot, watchEditBot, watchGetBot, watchGetCandlestick } from 'pages/bots/saga';

export default function* rootSaga() {
  yield all([
    watchPostRegistration(),
    watchPostLogin(),
    watchGetAccount(),
    watchBot(),
    watchCreateBot(),
    watchEditBot(),
    watchGetBot(),
    watchGetCandlestick(),
  ])
}