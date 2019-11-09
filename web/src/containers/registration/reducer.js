import { REGISTER_USER, REGISTER_USER_SUCCESS, REGISTER_USER_ERROR } from './actions';

// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
};

function registrationReducer(state = initialState, action) {
  switch (action.type) {
    case REGISTER_USER: {
      console.log(action.data)
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: action.data
      };

      return newState;
    }
    case REGISTER_USER_SUCCESS: {
      const newState = {
        ...state,
        loading: false,
        data: action.data
      };
      return newState;
    }

    case REGISTER_USER_ERROR: {
      return { ...state, error: action.error, loading: false };
    }
    default:
      return state;
  }
}

export default registrationReducer;
