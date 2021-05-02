export const GET_BALANCE = "GET_BALANCE";
export const BALANCE_SUCCESS = "BALANCE_SUCCESS";
export const BALANCE_ERROR = "BALANCE_ERROR";

export const GET_ASSETS = "GET_ASSETS";
export const GET_ASSETS_SUCCESS = "GET_ASSETS_SUCCESS";
export const GET_ASSETS_ERROR = "GET_ASSETS_ERROR";

export const UPDATE_ASSETS = "UPDATE_ASSETS";
export const UPDATE_ASSETS_SUCCESS = "UPDATE_ASSETS_SUCCESS";
export const UPDATE_ASSETS_ERROR = "UPDATE_ASSETS_ERROR";

export const BALANCE_DIFF = "BALANCE_DIFF";
export const BALANCE_DIFF_SUCCESS = "BALANCE_DIFF_SUCCESS";
export const BALANCE_DIFF_ERROR = "BALANCE_DIFF_ERROR";

export const GET_BALANCE_IN_BTC = "GET_BALANCE_IN_BTC";
export const GET_BALANCE_IN_BTC_SUCCESS = "GET_BALANCE_IN_BTC_SUCCESS";
export const GET_BALANCE_IN_BTC_ERROR = "GET_BALANCE_IN_BTC_ERROR";

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
 *
 * @return {object}      An action object with a type of BALANCE_SUCCESS passing the repos
 */
export function balanceSucceeded(res) {
  return {
    type: BALANCE_SUCCESS,
    isError: false,
    data: res,
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
    isError: false,
  };
}

export function getAssetsSucceeded(res) {
  return {
    type: GET_ASSETS_SUCCESS,
    isError: false,
    data: res.data,
  };
}

export function getAssetsFailed(error) {
  return {
    type: GET_ASSETS_ERROR,
    isError: true,
    data: error,
  };
}

/**
 * Update assets
 * /account/update-assets
 * @return {object} An action object with a type of BALANCE
 */
export function getBalanceDiff(days) {
  return {
    type: BALANCE_DIFF,
    isError: false,
    days: days,
  };
}

export function getBalanceDiffSucceeded(res) {
  return {
    type: BALANCE_DIFF_SUCCESS,
    isError: false,
    message: res.message,
    data: res.data,
  };
}

export function getBalanceDiffFailed(error) {
  return {
    type: BALANCE_DIFF_ERROR,
    isError: true,
    message: error.message,
  };
}

/**
 * Create new user
 *
 * @return {object} An action object with a type of BALANCE
 */
export function getBalanceInBtc() {
  return {
    type: GET_BALANCE_IN_BTC,
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
export function getBalanceInBtcSucceeded(res) {
  return {
    type: GET_BALANCE_IN_BTC_SUCCESS,
    isError: false,
    data: res,
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BALANCE_ERROR passing the error
 */
export function getBalanceInBtcFailed(error) {
  return {
    type: GET_BALANCE_IN_BTC_ERROR,
    isError: true,
    data: error,
  };
}
