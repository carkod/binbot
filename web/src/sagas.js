// index.js
import watchPostLogin from './containers/login/saga';
import watchBot, { watchCreateBot, watchEditBot, watchGetBot, watchGetCandlestick } from './pages/bots/saga';
import watchGetAccount, { watchAssetsValue, watchgetBtcChange, watchUpdateAssets } from './pages/dashboard/saga';
import { watchDeleteOpenOrders, watchGetOrders, watchOpenOrders, watchPollOrders } from './pages/orders/saga';
import { all } from 'redux-saga/effects';
import watchPostRegistration from './containers/registration/saga';

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
    watchGetOrders(),
    watchOpenOrders(),
    watchPollOrders(),
    watchDeleteOpenOrders(),
    watchAssetsValue(),
    watchUpdateAssets(),
    watchgetBtcChange(),
  ])
}