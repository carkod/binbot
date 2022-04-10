import produce from "immer";
import { checkValue } from "../../validations";
import {
  ADD_BLACKLIST,
  ADD_BLACKLIST_ERROR,
  ADD_BLACKLIST_SUCCESS,
  DELETE_BLACKLIST,
  DELETE_BLACKLIST_ERROR,
  DELETE_BLACKLIST_SUCCESS,
  GET_BLACKLIST,
  GET_BLACKLIST_ERROR,
  GET_BLACKLIST_SUCCESS,
  GET_RESEARCH,
  GET_RESEARCH_ERROR,
  GET_RESEARCH_SUCCESS,
  GET_SETTINGS,
  GET_SETTINGS_ERROR,
  GET_SETTINGS_SUCCESS,
  GET_TEST_AUTOTRADE_SETTINGS_SUCCESS
} from "./actions";

// The initial state of the App
export const initialState = {
  isError: false,
  data: null,
  message: null,
};

function researchReducer(state = initialState, action) {
  switch (action.type) {
    case GET_RESEARCH: {
      const newState = {
        ...state,
        data: action.data,
      };

      return newState;
    }
    case GET_RESEARCH_SUCCESS: {
      const newState = {
        ...state,

        isError: false,
        data: action.data,
      };
      return newState;
    }

    case GET_RESEARCH_ERROR: {
      return {
        ...state,
        error: action.error,

        isError: true,
      };
    }
    default:
      return state;
  }
}


const blacklistReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_BLACKLIST:
      return draft; // same as just 'return'
    case GET_BLACKLIST_SUCCESS:
      // OK: we return an entirely new state
      return {
        data: action.data,
      };
    case GET_BLACKLIST_ERROR:
      // OK: the immer way
      return;

    case ADD_BLACKLIST:
      return draft;
    case ADD_BLACKLIST_SUCCESS:
      if (!checkValue(action.data)) {
        draft.data.push(action.data);
        return {
          data: draft.data,
        };
      } else {
        return {
          data: draft.data,
        };
      }
    case ADD_BLACKLIST_ERROR:
      return;
    case DELETE_BLACKLIST:
      if (!checkValue(action.pair)) {
        return {
          data: draft.data.filter((x) => x !== action.pair),
        };
      } else {
        return draft.data;
      }
    case DELETE_BLACKLIST_SUCCESS:
      return action.payload;
    case DELETE_BLACKLIST_ERROR:
      return;
    default:
      break;
  }
}, {});

const settingsReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_SETTINGS:
      return draft; // same as just 'return'
    case GET_TEST_AUTOTRADE_SETTINGS_SUCCESS:
      draft.test_autotrade_settings = action.data;
      return draft
    case GET_SETTINGS_SUCCESS:
      // OK: we return an entirely new state
      return {
        data: action.data
      };
    case GET_SETTINGS_ERROR:
      // OK: the immer way
      return;
    case DELETE_BLACKLIST:
      return draft; // same as just 'return'
    case DELETE_BLACKLIST_SUCCESS:
      // OK: we return an entirely new state
      return action.payload;
    case DELETE_BLACKLIST_ERROR:
      // OK: the immer way
      return;
    default:
      break;
  }
}, {});

export {
  researchReducer,
  blacklistReducer,
  settingsReducer,
};
