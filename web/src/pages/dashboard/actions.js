export const GET_BALANCE = 'GET_BALANCE';
export const BALANCE_SUCCESS = 'BALANCE_SUCCESS';
export const BALANCE_ERROR = 'BALANCE_ERROR';
export const DEFAULT_LOCALE = 'en';

export const GET_ASSETS = 'GET_ASSETS';
export const GET_ASSETS_SUCCESS = 'GET_ASSETS_SUCCESS';
export const GET_ASSETS_ERROR = 'GET_ASSETS_ERROR';

export const UPDATE_ASSETS = 'UPDATE_ASSETS';
export const UPDATE_ASSETS_SUCCESS = 'UPDATE_ASSETS_SUCCESS';
export const UPDATE_ASSETS_ERROR = 'UPDATE_ASSETS_ERROR';

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

/**
 * Get assets
 * @return {object} An action object with a type of BALANCE
 */
export function getAssets() {
  return {
    type: GET_ASSETS,
    isLoading: true,
    isError: false,
  };
}

export function getAssetsSucceeded(res) {
  return {
    type: GET_ASSETS_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.data
  };
}

export function getAssetsFailed(error) {
  return {
    type: GET_ASSETS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}