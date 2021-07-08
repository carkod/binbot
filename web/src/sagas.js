// index.js
import { all } from "redux-saga/effects";
import watchPostLogin from "./containers/login/saga";
import watchPostRegistration from "./containers/registration/saga";
import watchBot, {
  watchActivateBot,
  watchCreateBot,
  watchDeactivateBot,
  watchEditBot,
  watchGetBot,
  watchGetCandlestick,
} from "./pages/bots/saga";
import {
  watchGbpBalanceApi,
  watchAssetsValue,
  watchGetBalanceDiff,
  watchGetBalanceInBtc,
} from "./pages/dashboard/saga";
import {
  watchDeleteOpenOrders,
  watchGetOrders,
  watchOpenOrders,
  watchPollOrders,
} from "./pages/orders/saga";
import { watchHistoricalResearchApi, watchResearchApi } from "./pages/research/saga";

export default function* rootSaga() {
  yield all([
    watchPostRegistration(),
    watchPostLogin(),
    watchGbpBalanceApi(),
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
    watchActivateBot(),
    watchDeactivateBot(),
    watchGetBalanceDiff(),
    watchGetBalanceInBtc(),
    watchResearchApi(),
    watchHistoricalResearchApi(),
  ]);
}
