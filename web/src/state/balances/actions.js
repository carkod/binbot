export const GET_BALANCE = "GET_BALANCE";
export const BALANCE_SUCCESS = "BALANCE_SUCCESS";
export const BALANCE_ERROR = "BALANCE_ERROR";

export const GET_BALANCE_RAW = "GET_BALANCE_RAW";
export const BALANCE_RAW_SUCCESS = "BALANCE_RAW_SUCCESS";
export const BALANCE_RAW_ERROR = "BALANCE_RAW_ERROR";
/**
 * Create new user
 *
 * @return {object} An action object with a type of BALANCE
 */
export function getBalance() {
  return {
    type: GET_BALANCE,
    isError: false,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 * @return {object}      An action object with a type of BALANCE_SUCCESS passing the repos
 */
export function balanceSucceeded(payload) {
  return {
    type: BALANCE_SUCCESS,
    ...payload
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 * @return {object}       An action object with a type of BALANCE_ERROR passing the error
 */
export function balanceFailed(error) {
  return {
    type: BALANCE_ERROR,
    data: error,
  };
}


/**
 * Create new user
 *
 * @return {object} An action object with a type of BALANCE
 */
 export function getBalanceRaw() {
  return {
    type: GET_BALANCE_RAW,
    isError: false,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 * @return {object}      An action object with a type of BALANCE_SUCCESS passing the repos
 */
export function balanceRawSucceeded(payload) {
  return {
    type: BALANCE_RAW_SUCCESS,
    ...payload
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BALANCE_ERROR passing the error
 */
export function balanceRawFailed(error) {
  return {
    type: BALANCE_RAW_ERROR,
    data: error,
  };
}