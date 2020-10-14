export const GET_BALANCE = 'GET_BALANCE';
export const BALANCE_SUCCESS = 'BALANCE_SUCCESS';
export const BALANCE_ERROR = 'BALANCE_ERROR';
export const DEFAULT_LOCALE = 'en';


/**
 * Create new user
 *
 * @return {object} An action object with a type of BALANCE
 */
export function getBalance() {
  return {
    type: GET_BALANCE,
    isLoading: true,
    isError: false,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object}      An action object with a type of BALANCE_SUCCESS passing the repos
 */
export function balanceSucceeded(res) {
  return {
    type: BALANCE_SUCCESS,
    isLoading: false,
    isError: false,
    data: res
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BALANCE_ERROR passing the error
 */
export function balanceFailed(error) {
  return {
    type: BALANCE_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}
