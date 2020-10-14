import { combineReducers } from 'redux';
import registrationReducer from './containers/registration/reducer';
import loginReducer from './containers/login/reducer';
import balanceReducer from './pages/dashboard/reducer';

const rootReducer = combineReducers({
  registrationReducer,
  loginReducer,
  balanceReducer,
})
export default rootReducer