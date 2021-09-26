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
        ...state,
        email: action.data.email,
        password: action.data.password,
        username: action.data.username
      }
      return newState;
    }
    case LOGIN_SUCCESS: {
      const newState = {
        ...state,
        access_token: action.data.access_token,
        email: action.data.email,
        username: action.data.username
      }
      return newState;
    }

    case LOGIN_ERROR: {
      if (action.isError) {
        return {
          ...state,
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
