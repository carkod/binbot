import { addNotification } from "../../validations";

export const GET_RESEARCH = "GET_RESEARCH";
export const GET_RESEARCH_SUCCESS = "GET_RESEARCH_SUCCESS";
export const GET_RESEARCH_ERROR = "GET_RESEARCH_ERROR";

export const GET_BLACKLIST = "GET_BLACKLIST";
export const GET_BLACKLIST_SUCCESS = "GET_BLACKLIST_SUCCESS";
export const GET_BLACKLIST_ERROR = "GET_BLACKLIST_ERROR";

export const ADD_BLACKLIST = "ADD_BLACKLIST";
export const ADD_BLACKLIST_SUCCESS = "ADD_BLACKLIST_SUCCESS";
export const ADD_BLACKLIST_ERROR = "ADD_BLACKLIST_ERROR";

export const DELETE_BLACKLIST = "DELETE_BLACKLIST";
export const DELETE_BLACKLIST_SUCCESS = "DELETE_BLACKLIST_SUCCESS";
export const DELETE_BLACKLIST_ERROR = "DELETE_BLACKLIST_ERROR";


export const GET_SETTINGS = "GET_SETTINGS";
export const GET_SETTINGS_SUCCESS = "GET_SETTINGS_SUCCESS";
export const GET_SETTINGS_ERROR = "GET_SETTINGS_ERROR";

export const EDIT_SETTINGS = "EDIT_SETTINGS";
export const EDIT_SETTINGS_SUCCESS = "EDIT_SETTINGS_SUCCESS";
export const EDIT_SETTINGS_ERROR = "EDIT_SETTINGS_ERROR";

/**
 * Dispatched when the repositories are loaded by the request saga
 *
 * @param  {array} repos The repository data
 * @param  {string} username The current username
 * @return {object} An action object with a type of BOT_SUCCESS passing the repos
 */
export function getResearchData(params) {
  return {
    type: GET_RESEARCH,
    isError: false,
    params
  };
}

/**
 * Dispatched when loading the repositories fails
 *
 * @param  {object} error The error
 * @return {object} An action object with a type of BOT_ERROR passing the error
 */
export function getResearchFailed(error) {
  addNotification("FAILED!", error.message, "error");
  return {
    type: GET_RESEARCH_ERROR,
    
    isError: true,
    data: error,
    message: error.message,
  };
}


export function getResearchSucceeded(res) {
  if (res.message) {
    addNotification("SUCCESS!", res.message, "error");
  }
  return {
    type: GET_RESEARCH_SUCCESS,
    isError: false,
    data: res.data,
  };
}

export function getBlacklist() {
  return {
    type: GET_BLACKLIST
  }
}

export function getBlacklistSucceeded(payload) {
  return {
    type: GET_BLACKLIST_SUCCESS,
    data: payload.data
  }
}

export function getBlacklistFailed() {
  return {
    type: GET_BLACKLIST_ERROR
  }
}

export function addBlackList(payload) {
  return {
    type: ADD_BLACKLIST,
    data: payload
  }
}

export function addBlackListSucceeded(payload) {
  if (payload.error === 1) {
    addNotification("ERROR!", payload.message, "error");
  } else {
    addNotification("SUCCESS!", payload.message, "success");
  }
  return {
    type: ADD_BLACKLIST_SUCCESS,
    data: payload.data
  }
}

export function addBlackListFailed() {
  return {
    type: ADD_BLACKLIST_ERROR
  }
}

export function deleteBlackList(payload) {
  return {
    type: DELETE_BLACKLIST,
    pair: payload
  }
}

export function deleteBlackListSucceeded(payload) {
  if (payload.error === 1) {
    addNotification("ERROR!", payload.message, "error");
  } else {
    addNotification("SUCCESS!", payload.message, "success");
  }
  return {
    type: DELETE_BLACKLIST_SUCCESS,
  }
}

export function deleteBlackListFailed() {
  return {
    type: DELETE_BLACKLIST_ERROR
  }
}

export function getSettings() {
  return {
    type: GET_SETTINGS
  }
}

export function getSettingsSucceeded(payload) {
  return {
    type: GET_SETTINGS_SUCCESS,
    data: payload.data
  }
}

export function getSettingsFailed() {
  return {
    type: GET_SETTINGS_ERROR
  }
}

export function editSettings(payload) {
  return {
    type: EDIT_SETTINGS,
    data: payload
  }
}

export function editSettingsSucceeded(payload) {
  if (payload.error === 1) {
    addNotification("FAILED!", payload.message, "error");
  } else {
    addNotification("SUCCESS!", payload.message, "success");
  }
  
  return {
    type: EDIT_SETTINGS_SUCCESS,
    data: payload.settings
  }
}

export function editSettingsFailed() {
  return {
    type: EDIT_SETTINGS_ERROR
  }
}
