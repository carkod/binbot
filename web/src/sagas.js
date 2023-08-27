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
  watchEditSettingsApi,
  watchGetBot,
  watchGetCandlestick,
  watchGetSettingsApi,
} from "./pages/bots/saga";
import { watchGetGainersLosers, watchBenchmarksApi } from "./pages/dashboard/saga";
import watchGetTestBotsApi, {
  watchActivateTestBotApi,
  watchCloseTestBotApi,
  watchCreateTestBot,
  watchDeactivateTestBotApi,
  watchDeleteTestbotApi,
  watchEditTestBotApi,
  watchGetTestBotApi,
  watchGetTestAutotradeSettingsApi,
  watchEditTestAutotradeSettings,
} from "./pages/paper-trading/saga";
import {
  watchAddBlacklistApi,
  watchDeleteBlackListApi,
  watchGetBlacklistApi,
  watchResearchApi,
} from "./pages/research/saga";
import watchUsersApi, {
  watchCreateUserApi,
  watchDeleteUserApi,
  watchEditUserApi,
} from "./pages/users/saga";
import {
  watchGetEstimate,
  watchRawBalance,
} from "./state/balances/saga";

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
    watchActivateBot(),
    watchDeactivateBot(),
    watchResearchApi(),
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
    watchGetTestBotsApi(),
    watchGetTestBotApi(),
    watchCreateTestBot(),
    watchEditTestBotApi(),
    watchCloseTestBotApi(),
    watchDeleteTestbotApi(),
    watchActivateTestBotApi(),
    watchDeactivateTestBotApi(),
    watchGetTestAutotradeSettingsApi(),
    watchEditTestAutotradeSettings(),
    watchGetGainersLosers(),
    watchBenchmarksApi(),
  ]);
}
