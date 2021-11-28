import request from "../../request";

export async function gbpHedge(asset) {
  const requestURL = `${process.env.REACT_APP_HEDGE_GBP}/${asset}`;
  const data = await request(requestURL);
  return data;
}
