import { LOGIN, LOGIN_SUCCESS, LOGIN_ERROR } from "./actions";

// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
};

function loginReducer(state = initialState, action) {
  switch (action.type) {
    case LOGIN: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data,
      };

      return newState;
    }
    case LOGIN_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.data,
      };
      return newState;
    }

    case LOGIN_ERROR: {
      return {
        ...state,
        error: action.error,
        isLoading: false,
        isError: true,
      };
    }
    default:
      return state;
  }
}

export default loginReducer;
