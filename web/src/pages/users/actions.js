import { addNotification } from "../../validations";

export const GET_USERS = "GET_USERS";
export const GET_USERS_SUCCESS = "GET_USERS_SUCCESS";
export const GET_USERS_ERROR = "GET_USERS_ERROR";

export const REGISTER_USER = "REGISTER_USER";
export const REGISTER_USER_SUCCESS = "REGISTER_USER_SUCCESS";
export const REGISTER_USER_ERROR = "REGISTER_USER_ERROR";
export const EDIT_USER = "EDIT_USER";
export const EDIT_USER_SUCCESS = "EDIT_USER_SUCCESS";
export const EDIT_USER_ERROR = "EDIT_USER_ERROR";
export const DELETE_USER = "DELETE_USER";
export const DELETE_USER_SUCCESS = "DELETE_USER_SUCCESS";
export const DELETE_USER_ERROR = "DELETE_USER_ERROR";

/**
 * Retrieve list of users
 * Optional id
 * @return {object} An action object with a type of BOT
 */
export function getUsers(id = null) {
  return {
    type: GET_USERS,
    id,
  };
}

/**
 * Retrieve list of users successful state
 *
 * @param  {array} response object with users in the data property
 * @return {object} redux state and payload
 */
export function getUsersSucceded(res) {
  return {
    type: GET_USERS_SUCCESS,
    users: res.data,
    message: res.message,
  };
}

/**
 * Network error, bad request errors, binance errors
 * @param  {object} { "error": 1, "message": "Failed to retrieve" }
 */
export function getUsersFailed(res) {
  return {
    type: GET_USERS_ERROR,
    message: res.message,
    error: res.error,
  };
}

/**
 * Edit an existent user
 * @return {object} with id required, returned to the saga to dispatch the API call
 */
export function editUser(payload) {
  return {
    type: EDIT_USER,
    data: payload,
    id: payload.id
  };
}

/**
 * Edit user successful state, nothing is returned, there maybe a success message
 * @return {object} Success message
 */
export function editUserSucceded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: EDIT_USER_SUCCESS,
    message: res.message,
  };
}

/**
 * Network error
 */
export function editUserFailed(res) {
  return {
    type: EDIT_USER_ERROR,
    data: res.error,
  };
}

/**
 * Create new bot
 *
 * @return {object} An action object with a type of BOT
 */
export function registerUser(payload) {
  return {
    type: REGISTER_USER,
    data: payload,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object} An action object with a type of BOT_SUCCESS passing the repos
 */
export function registerUserSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("Success!", res.message, "success");
  }

  return {
    type: REGISTER_USER_SUCCESS,
    message: res.message,
    data: res.data
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object} An action object with a type of BOT_ERROR passing the error
 */
export function registerUserFailed(res) {
  return {
    type: REGISTER_USER_ERROR,
    ...res,
  };
}

/**
 * Delete single user
 * @param {string} id of the user passed to saga
 * @return {object} An action object with a type of BOT
 */
export function deleteUser(id) {
  return {
    type: DELETE_USER,
    id: id,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object} An action object with a type of BOT_SUCCESS passing the repos
 */
export function deleteUserSucceeded(res) {
  if (res.error === 1) {
    addNotification("Delete user failed!", res.message, "error");
  } else {
    addNotification("Delete user succeeded", res.message, "success");
  }
  return {
    type: DELETE_USER_SUCCESS,
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object} An action object with a type of BOT_ERROR passing the error
 */
export function deleteUserFailed(error) {
  addNotification("FAILED!", error.message, "error");
  return {
    type: DELETE_USER_ERROR,
  };
}
