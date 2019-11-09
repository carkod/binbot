import { combineReducers } from 'redux';
import registrationReducer from './containers/registration/reducer';
import loginReducer from './containers/login/reducer';

const rootReducer = 
combineReducers({
  registrationReducer,
  loginReducer
})
export default rootReducer