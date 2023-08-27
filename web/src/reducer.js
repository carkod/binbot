import { reducer as toastrReducer } from "react-redux-toastr";
import { combineReducers } from "redux";
import loginReducer from "./containers/login/reducer";
import registrationReducer from "./containers/registration/reducer";
import { loadingReducer } from "./containers/spinner/reducer";
import {
  botReducer,
  candlestickReducer,
  symbolInfoReducer,
  symbolReducer,
} from "./pages/bots/reducer";
import { testBotsReducer } from "./pages/paper-trading/reducer";
import { settingsReducer } from "./pages/bots/reducer";
import { blacklistReducer } from "./pages/research/reducer";
import { usersReducer } from "./pages/users/reducer";
import {
  balanceRawReducer,
  estimateReducer,
} from "./state/balances/reducer";
import { gainersLosersReducer, btcBenchmarkReducer } from "./pages/dashboard/reducer";

const rootReducer = combineReducers({
  registrationReducer,
  loginReducer,
  balanceRawReducer,
  botReducer,
  symbolInfoReducer,
  symbolReducer,
  candlestickReducer,
  toastr: toastrReducer,
  loadingReducer,
  blacklistReducer,
  settingsReducer,
  estimateReducer,
  usersReducer,
  testBotsReducer,
  gainersLosersReducer,
  btcBenchmarkReducer,
});
export default rootReducer;
