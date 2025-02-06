const tokenName = "binbot-token";

export function getToken(): string {
  const token: string | null = window.localStorage.getItem(tokenName);
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
