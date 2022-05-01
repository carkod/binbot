import { reducer as toastrReducer } from "react-redux-toastr";
import { combineReducers } from "redux";
import loginReducer from "./containers/login/reducer";
import registrationReducer from "./containers/registration/reducer";
import { loadingReducer } from "./containers/spinner/reducer";
import {
  botReducer, candlestickReducer, editBotReducer, getSingleBotReducer, symbolInfoReducer,
  symbolReducer
} from "./pages/bots/reducer";
import { blacklistReducer, settingsReducer } from "./pages/research/reducer";
import {
  balanceRawReducer, balanceReducer, estimateReducer
} from "./state/balances/reducer";
import { usersReducer } from "./pages/users/reducer";
import { testBotsReducer } from "./pages/paper-trading/reducer";

const rootReducer = combineReducers({
  registrationReducer,
  loginReducer,
  balanceReducer,
  balanceRawReducer,
  botReducer,
  symbolInfoReducer,
  symbolReducer,
  getSingleBotReducer,
  editBotReducer,
  candlestickReducer,
  toastr: toastrReducer,
  loadingReducer,
  blacklistReducer,
  settingsReducer,
  estimateReducer,
  usersReducer,
  testBotsReducer,
});
export default rootReducer;
