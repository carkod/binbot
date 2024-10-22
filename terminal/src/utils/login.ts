const tokenName = "binbot-token";
export function getToken() {
  const token: string | null = localStorage.getItem(tokenName) || null;
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
  localStorage.setItem(tokenName, stringifyToken);
}

export function removeToken() {
  localStorage.removeItem(tokenName);
}
