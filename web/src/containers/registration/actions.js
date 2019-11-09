/*
 * AppConstants
 * Each action has a corresponding type, which the reducer knows and picks up on.
 * To avoid weird typos between the reducer and the actions, we save them as
 * constants here. We prefix them with 'yourproject/YourComponent' so we avoid
 * reducers accidentally picking up actions they shouldn't.
 *
 * Follow this format:
 * export const YOUR_ACTION_CONSTANT = 'yourproject/YourContainer/YOUR_ACTION_CONSTANT';
 */

export const REGISTER_USER = 'REGISTER_USER';
export const REGISTER_USER_SUCCESS = 'REGISTER_USER_SUCCESS';
export const REGISTER_USER_ERROR = 'REGISTER_USER_ERROR';
export const DEFAULT_LOCALE = 'en';


/**
 * Create new user
 *
 * @return {object} An action object with a type of REGISTER_USER
 */
export function registerUser(body) {
  return {
    type: REGISTER_USER,
    isLoading: true,
    isError: false,
    data: body
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object}      An action object with a type of REGISTER_USER_SUCCESS passing the repos
 */
export function registerUserSucceded(msg) {
  return {
    type: REGISTER_USER_SUCCESS,
    isLoading: false,
    isError: false,
    message: msg
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of REGISTER_USER_ERROR passing the error
 */
export function registerUserFailed(error) {
  return {
    type: REGISTER_USER_ERROR,
    isLoading: false,
    isError: true,
    message: error
  };
}
