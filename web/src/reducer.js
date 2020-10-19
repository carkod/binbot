import { combineReducers } from 'redux';
import registrationReducer from './containers/registration/reducer';
import loginReducer from './containers/login/reducer';
import balanceReducer from './pages/dashboard/reducer';
import { botReducer, symbolInfoReducer, symbolReducer, getSingleBotReducer, editBotReducer } from './pages/bots/reducer';

const rootReducer = combineReducers({
  registrationReducer,
  loginReducer,
  balanceReducer,
  botReducer,
  symbolInfoReducer,
  symbolReducer,
  getSingleBotReducer,
  editBotReducer,
})
export default rootReducer