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
} from "./actions";

// The initial state of the App
export const initialState = {
  isError: false,
  data: null,
  message: null,
};

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


export { blacklistReducer };
