/**
 * Parses the JSON returned by a network request
 *
 * @param  {object} response A response from a network request
 * @return {object}          The parsed JSON from the request
 */
function parseJSON(response) {
  if (response.status === 204 || response.status === 205) {
    return null;
  }
  return response.json();
}

/**
 * Checks if a network request came back fine, and throws an error if not
 *
 * @param  {object} response   A response from a network request
 * @return {object|undefined} Returns either the response, or throws an error
 */
function checkStatus(response) {


  if (response.status >= 200 && response.status < 300) {
    return response;
  }

  if (response.status < 404) {
    return response;
  }

  // throw error if error = 1
  if (response.json()["error"]) {
    throw new Error(response.json()["message"])
  }

  const error = new Error(response.statusText);
  error.response = response;
  throw error;
}

/**
 * Requests a URL, returning a promise
 *
 * @param  {string} url       The URL we want to request
 * @param  {object} [options] The options we want to pass to "fetch"
 *
 * @return {object}           The response data
 */
export default function request(url, options = {}) {
  return fetch(url, options).then(checkStatus).then(parseJSON);
}

const tokenName = "binbot-token";

export function getToken() {
  const token = localStorage.getItem(tokenName);
  if (token === "undefined" || token === "null" || token === "") {
    return null;
  }
  return JSON.parse(token);;
}

export function setToken(token) {
  const stringifyToken = JSON.stringify(token);
  localStorage.setItem(tokenName, stringifyToken);
}

export function removeToken() {
  localStorage.removeItem(tokenName);
}

export const defaultOptions = {
  method: "GET",
  mode: "cors", // no-cors, *cors, same-origin
  cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
};
