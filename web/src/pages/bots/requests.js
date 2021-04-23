import { defaultOptions } from "../../request";

export async function getQuoteAsset(pair) {
  const requestURL = `${process.env.REACT_APP_QUOTE_ASSET}/${pair}`;
  const res = await fetch(requestURL, defaultOptions);
  return res.json();
}

export async function getBaseAsset(pair) {
  const requestURL = `${process.env.REACT_APP_BASE_ASSET}/${pair}`;
  const res = await fetch(requestURL, defaultOptions);
  return res.json();
}
