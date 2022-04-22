import { addNotification } from "../../validations";

export const GET_BOTS = "GET_BOTS";
export const GET_BOTS_SUCCESS = "GET_BOTS_SUCCESS";
export const GET_BOTS_ERROR = "GET_BOTS_ERROR";

export const GET_BOT = "GET_BOT";
export const GET_BOT_SUCCESS = "GET_BOT_SUCCESS";
export const GET_BOT_ERROR = "GET_BOT_ERROR";

export const CREATE_BOT = "CREATE_BOT";
export const CREATE_BOT_SUCCESS = "CREATE_BOT_SUCCESS";
export const CREATE_BOT_ERROR = "CREATE_BOT_ERROR";
export const EDIT_BOT = "EDIT_BOT";
export const EDIT_BOT_SUCCESS = "EDIT_BOT_SUCCESS";
export const EDIT_BOT_ERROR = "EDIT_BOT_ERROR";
export const DELETE_BOT = "DELETE_BOT";
export const DELETE_BOT_SUCCESS = "DELETE_BOT_SUCCESS";
export const DELETE_BOT_ERROR = "DELETE_BOT_ERROR";
export const CLOSE_BOT = "CLOSE_BOT";

export const ACTIVATE_BOT = "ACTIVATE_BOT";
export const ACTIVATE_BOT_SUCCESS = "ACTIVATE_BOT_SUCCESS";
export const ACTIVATE_BOT_ERROR = "ACTIVATE_BOT_ERROR";
export const DEACTIVATE_BOT = "DEACTIVATE_BOT";
export const DEACTIVATE_BOT_SUCCESS = "DEACTIVATE_BOT_SUCCESS";
export const DEACTIVATE_BOT_ERROR = "DEACTIVATE_BOT_ERROR";

export const GET_SYMBOLS = "GET_SYMBOLS";
export const GET_SYMBOLS_SUCCESS = "GET_SYMBOLS_SUCCESS";
export const GET_SYMBOLS_ERROR = "GET_SYMBOLS_ERROR";
export const GET_SYMBOL_INFO = "GET_SYMBOL_INFO";
export const GET_SYMBOL_INFO_SUCCESS = "GET_SYMBOL_INFO_SUCCESS";
export const GET_SYMBOL_INFO_ERROR = "GET_SYMBOL_INFO_ERROR";

export const LOAD_CANDLESTICK = "LOAD_CANDLESTICK";
export const LOAD_CANDLESTICK_SUCCESS = "LOAD_CANDLESTICK_SUCCESS";
export const LOAD_CANDLESTICK_ERROR = "LOAD_CANDLESTICK_ERROR";

export const GET_QUOTE_ASSET = "GET_QUOTE_ASSET";
export const GET_QUOTE_ASSET_SUCCESSFUL = "GET_QUOTE_ASSET_SUCCESSFUL";
export const GET_QUOTE_ASSET_ERROR = "GET_QUOTE_ASSET_ERROR";

export const GET_BASE_ASSET = "GET_BASE_ASSET";
export const GET_BASE_ASSET_SUCCESSFUL = "GET_BASE_ASSET_SUCCESSFUL";
export const GET_BASE_ASSET_ERROR = "GET_BASE_ASSET_ERROR";

export const ARCHIVE_BOT = "ARCHIVE_BOT";
export const ARCHIVE_BOT_SUCCESS = "ARCHIVE_BOT_SUCCESS";
export const ARCHIVE_BOT_ERROR = "ARCHIVE_BOT_ERROR";

export const FILTER_BY_WEEK = "FILTER_BY_WEEK";
export const FILTER_BY_MONTH = "FILTER_BY_MONTH";

/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getBots() {
  return {
    type: GET_BOTS,
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
    isError: false,
    bots: res.data,
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
    isError: false,
    data: id,
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
    bots: res.data,
    message: res.message,
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
    data: body,
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
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  
  return {
    type: CREATE_BOT_SUCCESS,
    botId: res.botId,
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
  addNotification("FAILED!", error.message, "error");
  return {
    type: CREATE_BOT_ERROR,
    data: error,
    message: error.message,
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
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: EDIT_BOT_SUCCESS,
    bots: res,
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
  addNotification("FAILED!", error.message, "error");
  return {
    type: EDIT_BOT_ERROR,
    data: error,
  };
}

/**
 * Simple Delete bot
 * @return {objectId} 
 */
export function deleteBot(id) {
  return {
    type: DELETE_BOT,
    data: id,
    removeId: id
  };
}
/**
 * Close deal, sell coins and delete bot
 * @return {objectId} 
 */
export function closeBot(id) {
  return {
    type: CLOSE_BOT,
    data: id,
    removeId: id
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
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: DELETE_BOT_SUCCESS,
    message: res.message,
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
  addNotification("ERROR!", error.message, "error");
  return {
    type: DELETE_BOT_SUCCESS,
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
    data: id,
  };
}

export function activateBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: ACTIVATE_BOT_SUCCESS,
    data: res.botId,
  };
}

export function activateBotFailed(error) {
  addNotification("Failed to fetch", error.message, "error");
  return {
    type: ACTIVATE_BOT_ERROR,
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
    data: id,
  };
}

export function deactivateBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: DEACTIVATE_BOT_SUCCESS,
    data: res.botId,
    message: res.message,
  };
}

export function deactivateBotFailed(error) {
  return {
    type: DEACTIVATE_BOT_ERROR,
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
  };
}

export function getSymbolsSucceeded(res) {
  return {
    type: GET_SYMBOLS_SUCCESS,
    data: res.data,
  };
}

export function getSymbolsFailed(error) {
  return {
    type: GET_SYMBOLS_ERROR,
    error: error.message,
  };
}

export function getSymbolInfo(pair) {
  return {
    type: GET_SYMBOL_INFO,
    data: pair,
  };
}

export function getSymbolInfoSucceeded(res) {
  return {
    type: GET_SYMBOL_INFO_SUCCESS,
    data: res.data,
  };
}

export function getSymbolInfoFailed(error) {
  return {
    type: GET_SYMBOL_INFO_ERROR,
    error: error.message,
  };
}

export function loadCandlestick(pair, interval, start_time) {
  return {
    type: LOAD_CANDLESTICK,
    trace: null,
    layout: null,
    pair,
    interval,
    start_time
  };
}

export function loadCandlestickSucceeded(payload) {
  if (payload.error === 1) {
    addNotification("Some errors encountered", payload.message, "error");
  } else {
    addNotification("SUCCESS!", payload.message, "success");
  }
  return {
    type: LOAD_CANDLESTICK_SUCCESS,
    payload,
  };
}

export function loadCandlestickFailed(payload) {
  return {
    type: LOAD_CANDLESTICK_ERROR,
    payload,
  };
}

export function archiveBot(id) {
  return {
    type: ARCHIVE_BOT,
    id: id,
  };
}

export function archiveBotSucceeded(payload) {
  return {
    type: ARCHIVE_BOT_SUCCESS,
    id: payload.botId,
  };
}

export function archiveBotFailed(payload) {
  return {
    type: ARCHIVE_BOT_ERROR,
    id: payload.botId,
  };
}

export function filterByWeek() {
  return {
    type: FILTER_BY_WEEK,
  }
}

export function filterByMonth() {
  return {
    type: FILTER_BY_MONTH,
  }
}
