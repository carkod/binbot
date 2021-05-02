import { LOADING } from "./actions";

function loadingReducer(state = {
  loading: false
}, action = {}) {
  switch (action.type) {
    case LOADING: {
      return {
        ...state,
        loading: action.loading
      };
    }
    default:
      return state;
  }
}

export {
  loadingReducer,
};
