export const GET_BALANCE_RAW = "GET_BALANCE_RAW";
export const BALANCE_RAW_SUCCESS = "BALANCE_RAW_SUCCESS";
export const BALANCE_RAW_ERROR = "BALANCE_RAW_ERROR";

export const GET_ESTIMATE = "GET_ESTIMATE";
export const GET_ESTIMATE_SUCCESS = "ESTIMATE_SUCCESS";
export const GET_ESTIMATE_ERROR = "ESTIMATE_ERROR";

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

/**
 * Create new user
 *
 * @return {object} An action object with a type of BALANCE
 */
 export function getEstimate() {
  return {
    type: GET_ESTIMATE,
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 * @return {object}      An action object with a type of BALANCE_SUCCESS passing the repos
 */
export function getEstimateSucceeded(payload) {
  return {
    type: GET_ESTIMATE_SUCCESS,
    ...payload
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 * @return {object}       An action object with a type of GET_ESTIMATE_ERROR passing the error
 */
export function getEstimateFailed(error) {
  return {
    type: GET_ESTIMATE_ERROR,
    error
  };
}