import { setToken } from "../../request";
import { addNotification } from "../../validations";

export const LOGIN = "LOGIN";
export const LOGIN_SUCCESS = "LOGIN_SUCCESS";
export const LOGIN_ERROR = "LOGIN_ERROR";
export const DEFAULT_LOCALE = "en";

/**
 * Create new user
 *
 * @return {object} An action object with a type of LOGIN
 */
export function login(body) {
  return {
    type: LOGIN,
    isLoading: true,
    isError: false,
    data: body,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object}      An action object with a type of LOGIN_SUCCESS passing the repos
 */
export function loginSucceeded(res) {
  if (res.error > 0) {
    addNotification("ERROR!", res.message, "error");
    return {
      type: LOGIN_ERROR,
      isLoading: false,
      isError: true,
      message: res.message,
    };  
  }
  setToken(res.access_token);
  return {
    type: LOGIN_SUCCESS,
    isLoading: false,
    isError: false,
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of LOGIN_ERROR passing the error
 */
export function loginFailed(error) {
  return {
    type: LOGIN_ERROR,
    isLoading: false,
    isError: true,
    message: error.message,
  };
}
