import { addNotification } from "../../validations";

export const GET_BOTS = 'GET_BOTS';
export const GET_BOTS_SUCCESS = 'GET_BOTS_SUCCESS';
export const GET_BOTS_ERROR = 'GET_BOTS_ERROR';

export const GET_BOT = 'GET_BOT';
export const GET_BOT_SUCCESS = 'GET_BOT_SUCCESS';
export const GET_BOT_ERROR = 'GET_BOT_ERROR';

export const CREATE_BOT = 'CREATE_BOT';
export const CREATE_BOT_SUCCESS = 'CREATE_BOT_SUCCESS';
export const CREATE_BOT_ERROR = 'CREATE_BOT_ERROR';
export const EDIT_BOT = 'EDIT_BOT';
export const EDIT_BOT_SUCCESS = 'EDIT_BOT_SUCCESS';
export const EDIT_BOT_ERROR = 'EDIT_BOT_ERROR';
export const DELETE_BOT = 'DELETE_BOT';
export const DELETE_BOT_SUCCESS = 'DELETE_BOT_SUCCESS';
export const DELETE_BOT_ERROR = 'DELETE_BOT_ERROR';

export const ACTIVATE_BOT = 'ACTIVATE_BOT';
export const ACTIVATE_BOT_SUCCESS = 'ACTIVATE_BOT_SUCCESS';
export const ACTIVATE_BOT_ERROR = 'ACTIVATE_BOT_ERROR';
export const DEACTIVATE_BOT = 'DEACTIVATE_BOT';
export const DEACTIVATE_BOT_SUCCESS = 'DEACTIVATE_BOT_SUCCESS';
export const DEACTIVATE_BOT_ERROR = 'DEACTIVATE_BOT_ERROR';

export const GET_SYMBOLS = 'GET_SYMBOLS';
export const GET_SYMBOLS_SUCCESS = 'GET_SYMBOLS_SUCCESS';
export const GET_SYMBOLS_ERROR = 'GET_SYMBOLS_ERROR';
export const GET_SYMBOL_INFO = 'GET_SYMBOL_INFO';
export const GET_SYMBOL_INFO_SUCCESS = 'GET_SYMBOL_INFO_SUCCESS';
export const GET_SYMBOL_INFO_ERROR = 'GET_SYMBOL_INFO_ERROR';

export const LOAD_CANDLESTICK = 'LOAD_CANDLESTICK';
export const LOAD_CANDLESTICK_SUCCESS = 'LOAD_CANDLESTICK_SUCCESS';
export const LOAD_CANDLESTICK_ERROR = 'LOAD_CANDLESTICK_ERROR';
export const DEFAULT_LOCALE = 'en';


/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getBots() {
  return {
    type: GET_BOTS,
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
 * @return {object}      An action object with a type of BOT_SUCCESS passing the repos
 */
export function getBotsSucceeded(res) {
  return {
    type: GET_BOTS_SUCCESS,
    isLoading: false,
    isError: false,
    bots: res.data
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BOT_ERROR passing the error
 */
export function getBotsFailed(error) {
  return {
    type: GET_BOTS_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}

/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getBot(id) {
  return {
    type: GET_BOT,
    isLoading: true,
    isError: false,
    data: id
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
export function getBotSucceeded(res) {
  return {
    type: GET_BOT_SUCCESS,
    isLoading: false,
    isError: false,
    bots: res.data,
    message: res.message
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object}       An action object with a type of BOT_ERROR passing the error
 */
export function getBotFailed(error) {
  return {
    type: GET_BOT_ERROR,
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
export function createBot(body) {
  return {
    type: CREATE_BOT,
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
 * @return {object} An action object with a type of BOT_SUCCESS passing the repos
 */
export function createBotSucceeded(res) {
  return {
    type: CREATE_BOT_SUCCESS,
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
export function createBotFailed(error) {
  return {
    type: CREATE_BOT_ERROR,
    isLoading: false,
    isError: true,
    data: error,
    message: error.message
  };
}


/**
 * Edit bot
 *
 * @return {object} An action object with a type of BOT
 */
export function editBot(id, body) {
  return {
    type: EDIT_BOT,
    isLoading: true,
    isError: false,
    data: body,
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
export function editBotSucceeded(res) {
  return {
    type: EDIT_BOT_SUCCESS,
    isLoading: false,
    isError: false,
    bots: res
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 *
 * @return {object} An action object with a type of BOT_ERROR passing the error
 */
export function editBotFailed(error) {
  return {
    type: EDIT_BOT_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}

/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function deleteBot(id) {
  return {
    type: DELETE_BOT,
    isLoading: true,
    isError: false,
    data: id
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
export function deleteBotSucceeded(res) {
  return {
    type: DELETE_BOT_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.botId,
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
export function deleteBotFailed(error) {
  return {
    type: DELETE_BOT_SUCCESS,
    isLoading: false,
    isError: true,
    error: error.message,
  };
}


/**
 * Activate bot
 * GET /bot/activate/<id>
 * @return {object} An action object with a type of BOT
 */
export function activateBot(id) {
  return {
    type: ACTIVATE_BOT,
    isLoading: true,
    isError: false,
    data: id
  };
}

export function activateBotSucceeded(res) {
  addNotification(ACTIVATE_BOT_SUCCESS, res.message)
  return {
    type: ACTIVATE_BOT_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.botId,
  };
}

export function activateBotFailed(error) {
  return {
    type: ACTIVATE_BOT_SUCCESS,
    isLoading: false,
    isError: true,
    error: error.message,
  };
}

/**
 * Deactivate bot
 * GET /bot/deactivate/<id>
 * @return {object} An action object with a type of BOT
 */
export function deactivateBot(id) {
  return {
    type: DEACTIVATE_BOT,
    isLoading: true,
    isError: false,
    data: id
  };
}

export function deactivateBotSucceeded(res) {
  return {
    type: DEACTIVATE_BOT_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.botId,
    message: res.message
  };
}

export function deactivateBotFailed(error) {
  return {
    type: DEACTIVATE_BOT_SUCCESS,
    isLoading: false,
    isError: true,
    error: error.message,
  };
}


/**
 * Get symbols
 *
 * @return {object} An action object with a type of BOT
 */
export function getSymbols() {
  return {
    type: GET_SYMBOLS,
    isLoading: false,
    isError: false,
  };
}

export function getSymbolsSucceeded(res) {
  return {
    type: GET_SYMBOLS_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.data
  };
}

export function getSymbolsFailed(error) {
  return {
    type: GET_SYMBOLS_ERROR,
    isLoading: false,
    isError: true,
    error: error.message,
  };
}

export function getSymbolInfo(pair) {
  return {
    type: GET_SYMBOL_INFO,
    isLoading: false,
    isError: false,
    data: pair,
  };
}

export function getSymbolInfoSucceeded(res) {
  return {
    type: GET_SYMBOL_INFO_SUCCESS,
    isLoading: false,
    isError: false,
    data: res.data
  };
}

export function getSymbolInfoFailed(error) {
  return {
    type: GET_SYMBOL_INFO_ERROR,
    isLoading: false,
    isError: true,
    error: error.message,
  };
}


export function loadCandlestick(pair, interval) {
  return {
    type: LOAD_CANDLESTICK,
    isLoading: true,
    isError: false,
    trace: null,
    layout: null,
    pair,
    interval,
  };
}

export function loadCandlestickSucceeded(payload) {
  return {
    type: LOAD_CANDLESTICK_SUCCESS,
    isLoading: true,
    isError: false,
    payload: {
      trace: [JSON.parse(payload.trace)]
    }
  };
}

export function loadCandlestickFailed(payload) {
  return {
    type: LOAD_CANDLESTICK_ERROR,
    isLoading: true,
    isError: false,
    payload
  };
}