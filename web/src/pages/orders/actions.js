export const GET_ALL_ORDERS = 'GET_ALL_ORDERS';
export const GET_ALL_ORDERS_SUCCESS = 'GET_ALL_ORDERS_SUCCESS';
export const GET_ALL_ORDERS_ERROR = 'GET_ALL_ORDERS_ERROR';

export const GET_OPEN_ORDERS = 'GET_OPEN_ORDERS';
export const GET_OPEN_ORDERS_SUCCESS = 'GET_OPEN_ORDERS_SUCCESS';
export const GET_OPEN_ORDERS_ERROR = 'GET_OPEN_ORDERS_ERROR';
export const DELETE_OPEN_ORDERS = 'DELETE_OPEN_ORDERS';
export const DELETE_OPEN_ORDERS_SUCCESS = 'DELETE_OPEN_ORDERS_SUCCESS';
export const DELETE_OPEN_ORDERS_ERROR = 'DELETE_OPEN_ORDERS_ERROR';

export const POLL_ORDERS = 'POLL_ORDERS';
export const POLL_ORDERS_SUCCESS = 'POLL_ORDERS_SUCCESS';
export const POLL_ORDERS_ERROR = 'POLL_ORDERS_ERROR';
export const DEFAULT_LOCALE = 'en';


/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getOrders({limit, offset, status}) {
  return {
    type: GET_ALL_ORDERS,
    isLoading: true,
    isError: false,
    data: {
      limit: limit,
      offset: offset,
      status: status
    }
  };
}

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 *
 * @return {object}      An action object with a type of BOT_SUCCESS passing the repos
 */
export function getOrdersSucceeded(res) {
  return {
    type: GET_ALL_ORDERS_SUCCESS,
    isLoading: false,
    isError: false,
    orders: res.data,
    pages: res.pages,
    status: res.status
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BOT_ERROR passing the error
 */
export function getOrdersFailed(error) {
  return {
    type: GET_ALL_ORDERS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}

/**
 * Get Open orders and its two states
 *
 * @return {object} An action object with a type of BOT
 */
export function getOpenOrders() {
  return {
    type: GET_OPEN_ORDERS,
    isLoading: true,
    isError: false,
  };
}

export function getOpenOrdersSucceeded(res) {
  return {
    type: GET_OPEN_ORDERS_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.data,
    message: res.message
  };
}

export function getOpenOrdersFailed(error) {
  return {
    type: GET_OPEN_ORDERS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}

/**
 * Delete/Cancel Open orders and its two states
 *
 * @return {object} An action object with a type of BOT
 */
export function deleteOpenOrders(payload) {
  return {
    type: DELETE_OPEN_ORDERS,
    isLoading: true,
    isError: false,
    data: payload
  };
}

export function deleteOpenOrdersSucceeded(res) {
  return {
    type: DELETE_OPEN_ORDERS_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.data,
    message: res.message
  };
}

export function deleteOpenOrdersFailed(error) {
  return {
    type: DELETE_OPEN_ORDERS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}

/**
 * Create new bot
 *
 * @return {object} An action object with a type of BOT
 */
export function pollOrders() {
  return {
    type: POLL_ORDERS,
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
 * @return {object} An action object with a type of BOT_SUCCESS passing the repos
 */
export function pollOrdersSucceeded(res) {
  return {
    type: POLL_ORDERS_SUCCESS,
    isLoading: false,
    isError: false,
    bots: res.botId,
    message: res.message
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object} An action object with a type of BOT_ERROR passing the error
 */
export function pollOrdersFailed(error) {
  return {
    type: POLL_ORDERS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
    message: error.message
  };
}
