import { reducer as toastrReducer } from "react-redux-toastr";
import { combineReducers } from "redux";
import loginReducer from "./containers/login/reducer";
import registrationReducer from "./containers/registration/reducer";
import { loadingReducer } from "./containers/spinner/reducer";
import {
  botReducer, candlestickReducer, editBotReducer, getSingleBotReducer, symbolInfoReducer,
  symbolReducer
} from "./pages/bots/reducer";
import { openOrdersReducer, ordersReducer } from "./pages/orders/reducer";
import { historicalResearchReducer, researchReducer, blacklistReducer, settingsReducer } from "./pages/research/reducer";
import {
  balanceRawReducer, balanceReducer, estimateReducer
} from "./state/balances/reducer";
import { usersReducer } from "./pages/users/reducer";

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
  ordersReducer,
  openOrdersReducer,
  toastr: toastrReducer,
  loadingReducer,
  researchReducer,
  historicalResearchReducer,
  blacklistReducer,
  settingsReducer,
  estimateReducer,
  usersReducer
});
export default rootReducer;
