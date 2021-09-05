// index.js
import { all } from "redux-saga/effects";
import watchPostLogin from "./containers/login/saga";
import watchPostRegistration from "./containers/registration/saga";
import watchBot, {
  watchActivateBot,
  watchcloseBotApi,
  watchCreateBot,
  watchDeactivateBot,
  watchEditBot,
  watchGetBot,
  watchGetCandlestick,
} from "./pages/bots/saga";
import {
  watchDeleteOpenOrders,
  watchGetOrders,
  watchOpenOrders,
  watchPollOrders,
} from "./pages/orders/saga";
import { watchHistoricalResearchApi, watchResearchApi } from "./pages/research/saga";
import { watchGetBalanceApi, watchRawBalance } from "./state/balances/saga";

export default function* rootSaga() {
  yield all([
    watchPostRegistration(),
    watchPostLogin(),
    watchBot(),
    watchCreateBot(),
    watchEditBot(),
    watchGetBot(),
    watchcloseBotApi(),
    watchGetCandlestick(),
    watchGetOrders(),
    watchOpenOrders(),
    watchPollOrders(),
    watchDeleteOpenOrders(),
    watchActivateBot(),
    watchDeactivateBot(),
    watchResearchApi(),
    watchHistoricalResearchApi(),
    watchGetBalanceApi(),
    watchRawBalance(),
  ]);
}
