import { addNotification } from "../../validations";

export const GET_TEST_BOTS = "GET_TEST_BOTS";
export const GET_TEST_BOTS_SUCCESS = "GET_TEST_BOTS_SUCCESS";
export const GET_TEST_BOTS_ERROR = "GET_TEST_BOTS_ERROR";

export const GET_TEST_BOT = "GET_TEST_BOT";
export const GET_TEST_BOT_SUCCESS = "GET_TEST_BOT_SUCCESS";
export const GET_TEST_BOT_ERROR = "GET_TEST_BOT_ERROR";

export const CREATE_TEST_BOT = "CREATE_TEST_BOT";
export const CREATE_TEST_BOT_SUCCESS = "CREATE_TEST_BOT_SUCCESS";
export const CREATE_TEST_BOT_ERROR = "CREATE_TEST_BOT_ERROR";
export const EDIT_TEST_BOT = "EDIT_TEST_BOT";
export const EDIT_TEST_BOT_SUCCESS = "EDIT_TEST_BOT_SUCCESS";
export const EDIT_TEST_BOT_ERROR = "EDIT_TEST_BOT_ERROR";
export const DELETE_TEST_BOT = "DELETE_TEST_BOT";
export const DELETE_TEST_BOT_SUCCESS = "DELETE_TEST_BOT_SUCCESS";
export const DELETE_TEST_BOT_ERROR = "DELETE_TEST_BOT_ERROR";
export const CLOSE_TEST_BOT = "CLOSE_TEST_BOT";

export const ACTIVATE_TEST_BOT = "ACTIVATE_TEST_BOT";
export const ACTIVATE_TEST_BOT_SUCCESS = "ACTIVATE_TEST_BOT_SUCCESS";
export const ACTIVATE_TEST_BOT_ERROR = "ACTIVATE_TEST_BOT_ERROR";
export const DEACTIVATE_TEST_BOT = "DEACTIVATE_TEST_BOT";
export const DEACTIVATE_TEST_BOT_SUCCESS = "DEACTIVATE_TEST_BOT_SUCCESS";
export const DEACTIVATE_TEST_BOT_ERROR = "DEACTIVATE_TEST_BOT_ERROR";

export const SET_BOT_STATE = "SET_BOT_STATE";


export function setBotState(payload) {
  return {
      type: SET_BOT_STATE,
      payload
  }
}

/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getTestBots() {
  return {
    type: GET_TEST_BOTS,
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
export function getTestBotsSucceeded(res) {
  return {
    type: GET_TEST_BOTS_SUCCESS,
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
export function getTestBotsFailed(error) {
  return {
    type: GET_TEST_BOTS_ERROR,
    isError: true,
    data: error,
  };
}

/**
 * Create new user
 *
 * @return {object} An action object with a type of BOT
 */
export function getTestBot(id) {
  return {
    type: GET_TEST_BOT,
    id: id,
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
export function getTestBotSucceeded(res) {
  return {
    type: GET_TEST_BOT_SUCCESS,
    bot: res.data,
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
export function getTestBotFailed(error) {
  return {
    type: GET_TEST_BOT_ERROR,
    data: error,
  };
}

/**
 * Create new bot
 *
 * @return {object} An action object with a type of BOT
 */
export function createTestBot(body) {
  return {
    type: CREATE_TEST_BOT,
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
export function createTestBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  
  return {
    type: CREATE_TEST_BOT_SUCCESS,
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
export function createTestBotFailed(error) {
  addNotification("FAILED!", error.message, "error");
  return {
    type: CREATE_TEST_BOT_ERROR,
    data: error,
    message: error.message,
  };
}

/**
 * Edit bot
 *
 * @return {object} An action object with a type of BOT
 */
export function editTestBot(id, body) {
  return {
    type: EDIT_TEST_BOT,
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
export function editTestBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: EDIT_TEST_BOT_SUCCESS,
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
export function editTestBotFailed(error) {
  addNotification("FAILED!", error.message, "error");
  return {
    type: EDIT_TEST_BOT_ERROR,
    data: error,
  };
}

/**
 * Simple Delete bot
 * @return {objectId} 
 */
export function deleteTestBot(id) {
  return {
    type: DELETE_TEST_BOT,
    data: id,
    removeId: id
  };
}
/**
 * Close deal, sell coins and delete bot
 * @return {objectId} 
 */
export function closeTestBot(id) {
  return {
    type: CLOSE_TEST_BOT,
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
export function deleteTestBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: DELETE_TEST_BOT_SUCCESS,
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
export function deleteTestBotFailed(error) {
  addNotification("ERROR!", error.message, "error");
  return {
    type: DELETE_TEST_BOT_SUCCESS,
    error: error.message,
  };
}

/**
 * Activate bot
 * GET /bot/activate/<id>
 * @return {object} An action object with a type of BOT
 */
export function activateTestBot(id) {
  return {
    type: ACTIVATE_TEST_BOT,
    data: id,
  };
}

export function activateTestBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: ACTIVATE_TEST_BOT_SUCCESS,
    data: res.botId,
  };
}

export function activateTestBotFailed(error) {
  addNotification("Failed to fetch", error.message, "error");
  return {
    type: ACTIVATE_TEST_BOT_ERROR,
  };
}

/**
 * Deactivate bot
 * GET /bot/deactivate/<id>
 * @return {object} An action object with a type of BOT
 */
export function deactivateTestBot(id) {
  return {
    type: DEACTIVATE_TEST_BOT,
    data: id,
  };
}

export function deactivateTestBotSucceeded(res) {
  if (res.error === 1) {
    addNotification("Some errors encountered", res.message, "error");
  } else {
    addNotification("SUCCESS!", res.message, "success");
  }
  return {
    type: DEACTIVATE_TEST_BOT_SUCCESS,
    data: res.botId,
    message: res.message,
  };
}

export function deactivateTestBotFailed(error) {
  return {
    type: DEACTIVATE_TEST_BOT_ERROR,
    error: error.message,
  };
}
