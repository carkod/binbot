import request from "../../request";

// This file contains requests to API endpoints that don't require redux
// because it only serves for one read-only component


export async function getQuoteAsset(pair) {
  const requestURL = `${process.env.REACT_APP_QUOTE_ASSET}/${pair}`;
  const data = await request(requestURL);
  return data;
}

export async function getBaseAsset(pair) {
  const requestURL = `${process.env.REACT_APP_BASE_ASSET}/${pair}`;
  const data = await request(requestURL);
  return data;
}

export async function convertGBP(symbol) {
  const requestURL = `${process.env.REACT_APP_TICKER}/${symbol}`;
  const data = await request(requestURL);
  return data;
}
