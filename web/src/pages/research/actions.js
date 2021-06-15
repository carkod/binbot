import { addNotification } from "../../validations";

export const GET_RESEARCH = "GET_RESEARCH";
export const GET_RESEARCH_SUCCESS = "GET_RESEARCH_SUCCESS";
export const GET_RESEARCH_ERROR = "GET_RESEARCH_ERROR";


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
    isLoading: false,
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
    isLoading: false,
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
    isLoading: false,
    isError: false,
    data: res.data,
  };
}
