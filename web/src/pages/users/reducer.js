import produce from "immer";
import {
  DELETE_USER,
  DELETE_USER_ERROR,
  DELETE_USER_SUCCESS,
  EDIT_USER,
  EDIT_USER_ERROR,
  EDIT_USER_SUCCESS,
  GET_USERS,
  GET_USERS_ERROR,
  GET_USERS_SUCCESS,
  REGISTER_USER,
  REGISTER_USER_ERROR,
  REGISTER_USER_SUCCESS,
} from "./actions";

// The initial state of the App
export const initialState = {
  users: null,
  userId: null,
  deleteUserId: null,
};

const usersReducer = produce((draft, action) => {
  switch (action.type) {
    case GET_USERS: {
      return {
        users: draft.users,
        userId: action.id,
      };
    }
    case GET_USERS_SUCCESS: {
      draft.users = action.users;
      return draft;
    }

    case GET_USERS_ERROR: {
      return {
        users: draft.users,
        userId: draft.userId,
      };
    }

    case REGISTER_USER: {
      draft.userData = action.data
      return draft;
    }
    case REGISTER_USER_SUCCESS: {
      draft.users.push(action.data);
      return draft;
    }

    case REGISTER_USER_ERROR: {
      return {
        users: draft.users,
        userData: null,
      };
    }

    case EDIT_USER: {
      draft.userData = action.data;
      draft.userId = action.id
      return draft;
    }
    case EDIT_USER_SUCCESS: {
      const findIndex = action.users.findIndex(x => x.id.$oid === action.id);
      draft.users[findIndex] = action.data;
      return draft;
    }

    case EDIT_USER_ERROR: {
      return {
        users: draft.users,
        userData: null,
        userId: draft.userId,
      };
    }

    case DELETE_USER: {
      draft.deleteUserId = action.id
      return draft;
    }

    case DELETE_USER_SUCCESS: {
      const users = draft.users.filter((x) => x.id.$oid !== draft.deleteUserId);
      draft.users = users
      draft.deleteUserId = null;
      return draft;
    }

    case DELETE_USER_ERROR: {
      return {
        error: action.error,
        botActive: draft.botActive,
      };
    }

    default:
      break;
  }
}, initialState);

export { usersReducer };
