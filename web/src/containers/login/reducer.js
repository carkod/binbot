import { LOGIN, LOGIN_SUCCESS, LOGIN_ERROR } from "./actions";

// The initial state of the App
export const initialState = {
  access_token: null,
  email: null,
  password: null,
  username: null,
  error:0,
  message: null,
};

function loginReducer(state = initialState, action) {
  switch (action.type) {
    case LOGIN: {
      const newState = {
        password: action.data.password,
        username: action.data.email
      }
      return newState;
    }
    case LOGIN_SUCCESS: {
      const newState = {
        access_token: action.data.access_token,
        email: action.data.email,
      }
      return newState;
    }

    case LOGIN_ERROR: {
      if (action.isError) {
        return {
          error: true,
          message: action.message
        }
      }
      return {
        ...state,
        error: false,
        message: action.message,
      };
    }
    default:
      return state;
  }
}

export default loginReducer;
