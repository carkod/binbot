const tokenName = "binbot-token";

/**
 * Checks if a network request came back fine, and throws an error if not
 *
 * @param  {object} response   A response from a network request
 * @return {object|undefined} Returns either the response, or throws an error
 */
function checkStatus(response) {
  if (response.status === 401) {
    // Remove token as server is rejecting it
    removeToken();
    alert("User not authenticated");
    window.location = "/login";
  }

  if (response.status >= 200 && response.status < 300) {
    return response.json();
  }

  if (response.status < 404) {
    return response;
  }

  // throw error if error = 1
  if (response.json()["error"]) {
    throw new Error(response.json()["message"]);
  }

  let error = new Error(response.statusText);
  error.response = response;
  throw error;
}

export function getToken() {
  const token = localStorage.getItem(tokenName);
  if (token === "undefined" || token === "null" || token === "") {
    return null;
  }
  return JSON.parse(token);
}

export function setToken(token) {
  const stringifyToken = JSON.stringify(token);
  localStorage.setItem(tokenName, stringifyToken);
}

export function removeToken() {
  localStorage.removeItem(tokenName);
}

export function buildBackUrl() {
  let base = window.location.hostname.split(".");
  if (base.includes("localhost")) {
    base = ["localhost:8008"];
  } else {
    base.unshift("api");
  }
  base = `${window.location.protocol}//${base.join(".")}`;
  return base;
}

/**
 * Requests a URL, returning a promise
 *
 * @param  {string} url       The URL we want to request
 * @param  {object} [options] The options we want to pass to "fetch"
 *
 * @return {object}           The response data
 */
export default async function request(
  url,
  verb = "GET",
  body = undefined
) {

  const baseUrl = buildBackUrl();
  let options = {
    method: verb,
    mode: "cors",
    cache: "no-cache"
  };

  try {
    url = new URL(url)
  } catch (e) {
    if (e instanceof TypeError) {
      url = baseUrl + url
      const headers = new Headers({
        "content-type": "application/json",
        accept: "application/json",
        Authorization: `Bearer ${getToken()}`
      })
      options.headers = headers
    }
  }


  if (body) {
    options.body = JSON.stringify(body);
  }
  
  const response = await fetch(url, options);
  const content = await checkStatus(response);
  return content;
}


export async function requestForm(
  url,
  verb,
  formData
) {

  let options = {
    method: verb,
    mode: "cors",
    cache: "no-cache",
    body: formData,
  };

  const baseUrl = buildBackUrl();
  url = url instanceof URL ? url : baseUrl + url;
  const response = await fetch(url, options);
  const content = await checkStatus(response);
  return content;
}
