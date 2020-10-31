import { combineReducers } from 'redux';
import registrationReducer from './containers/registration/reducer';
import loginReducer from './containers/login/reducer';
import balanceReducer from './pages/dashboard/reducer';
import { botReducer, symbolInfoReducer, symbolReducer, getSingleBotReducer, editBotReducer, candlestickReducer } from './pages/bots/reducer';
import { ordersReducer, openOrdersReducer } from 'pages/orders/reducer'

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
})
export default rootReducer