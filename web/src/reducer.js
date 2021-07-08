import { combineReducers } from "redux";
import registrationReducer from "./containers/registration/reducer";
import loginReducer from "./containers/login/reducer";
import {
  balanceReducer,
} from "./state/balances/reducer";
import {
  botReducer,
  symbolInfoReducer,
  symbolReducer,
  getSingleBotReducer,
  editBotReducer,
  candlestickReducer,
} from "./pages/bots/reducer";
import { ordersReducer, openOrdersReducer } from "./pages/orders/reducer";
import { reducer as toastrReducer } from "react-redux-toastr";
import { loadingReducer } from "./containers/spinner/reducer";
import { researchReducer, historicalResearchReducer } from "./pages/research/reducer";

const rootReducer = combineReducers({
  registrationReducer,
  loginReducer,
  balanceReducer,
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
});
export default rootReducer;
