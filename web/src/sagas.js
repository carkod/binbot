// index.js
import { all } from "redux-saga/effects";
import watchPostLogin from "./containers/login/saga";
import watchPostRegistration from "./containers/registration/saga";
import watchGetBotApi, {
  watchActivateBot,
  watchArchiveBot,
  watchBot,
  watchcloseBotApi,
  watchCreateBot,
  watchDeactivateBot,
  watchDeleteBotApi,
  watchEditBot,
  watchGetBot,
  watchGetCandlestick
} from "./pages/bots/saga";
import {
  watchDeleteOpenOrders,
  watchGetOrders,
  watchOpenOrders,
  watchPollOrders
} from "./pages/orders/saga";
import {
  watchAddBlacklistApi,
  watchDeleteBlackListApi,
  watchEditSettingsApi,
  watchGetBlacklistApi,
  watchGetSettingsApi,
  watchHistoricalResearchApi,
  watchResearchApi
} from "./pages/research/saga";
import watchUsersApi, { watchCreateUserApi, watchDeleteUserApi, watchEditUserApi } from "./pages/users/saga";
import { watchGetBalanceApi, watchGetEstimate, watchRawBalance } from "./state/balances/saga";

export default function* rootSaga() {
  yield all([
    watchPostRegistration(),
    watchPostLogin(),
    watchBot(),
    watchGetBotApi(),
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
    watchDeleteBotApi(),
    watchArchiveBot(),
    watchGetBlacklistApi(),
    watchGetSettingsApi(),
    watchEditSettingsApi(),
    watchDeleteBlackListApi(),
    watchAddBlacklistApi(),
    watchGetEstimate(),
    watchUsersApi(),
    watchEditUserApi(),
    watchDeleteUserApi(),
    watchCreateUserApi(),
  ]);
}
