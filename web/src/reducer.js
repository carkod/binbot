import { combineReducers } from 'redux';
import registrationReducer from './containers/registration/reducer';
import loginReducer from './containers/login/reducer';
import { balanceReducer, assetsReducer, balanceDiffReducer } from './pages/dashboard/reducer';
import { botReducer, symbolInfoReducer, symbolReducer, getSingleBotReducer, editBotReducer, candlestickReducer } from './pages/bots/reducer';
import { ordersReducer, openOrdersReducer } from './pages/orders/reducer'
import {reducer as toastrReducer} from 'react-redux-toastr';

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
  assetsReducer,
  balanceDiffReducer,
  toastr: toastrReducer,
})
export default rootReducer