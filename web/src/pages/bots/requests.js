import { defaultOptions } from "../../request";

// This file contains requests to API endpoints that don't require redux
// because it only serves for one read-only component


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

export async function convertGBP(symbol) {
  const requestURL = `${process.env.REACT_APP_TICKER}/${symbol}`;
  const res = await fetch(requestURL, defaultOptions);
  return res.json();
}
