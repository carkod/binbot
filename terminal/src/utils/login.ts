const tokenName = "binbot-token";

type Token = {
  access_token: string;
  refresh_token: string;
}

export function getToken(): Token | null {
  const token: string | null = window.localStorage.getItem(tokenName) || null;
  if (
    token === "undefined" ||
    token === "null" ||
    token === "" ||
    token === null
  ) {
    return null;
  } else {
    return JSON.parse(token);
  }
}

export function setToken(token: string) {
  const stringifyToken = JSON.stringify(token);
  window.localStorage.setItem(tokenName, stringifyToken);
}

export function removeToken() {
  window.localStorage.removeItem(tokenName);
}
