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
export function getBot() {
  return {
    type: GET_BOT,
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
export function getBotSucceeded(res) {
  return {
    type: GET_BOT_SUCCESS,
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
export function createBot() {
  return {
    type: CREATE_BOT,
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
export function createBotSucceeded(res) {
  return {
    type: CREATE_BOT_SUCCESS,
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
export function createBotFailed(error) {
  return {
    type: CREATE_BOT_ERROR,
    isLoading: false,
    isError: true,
    data: error,
  };
}


/**
 * Edit bot
 *
 * @return {object} An action object with a type of BOT
 */
export function editBot() {
  return {
    type: EDIT_BOT,
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
export function deleteBot() {
  return {
    type: DELETE_BOT,
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
export function deleteBotSucceeded(res) {
  return {
    type: DELETE_BOT_SUCCESS,
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
export function deleteBotFailed(error) {
  return {
    type: DELETE_BOT_SUCCESS,
    isLoading: false,
    isError: true,
    data: error,
  };
}