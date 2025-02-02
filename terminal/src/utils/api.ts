import { fetchBaseQuery } from "@reduxjs/toolkit/query";
import { Bounce, toast } from "react-toastify";
import { getToken } from "./login";
import { type Bot } from "../features/bots/botInitialState";

export function buildBackUrl() {
  let base = window.location.hostname.split(".");
  if (base.includes("localhost")) {
    base = ["localhost:8008"];
  } else {
    base.unshift("api");
  }
  const backUrl = `${window.location.protocol}//${base.join(".")}`;
  return backUrl;
}

export const binbotBaseQuery = fetchBaseQuery({
  baseUrl: buildBackUrl(),
  prepareHeaders: (headers) => {
    const token = getToken();

    if (token) {
      headers.set("Authorization", `Bearer ${token.access_token}`);
    }
    return headers;
  },
});

export const binanceBaseQuery = fetchBaseQuery({
  baseUrl: "https://api.binance.com/api/v3",
});

export const defaultResponseHandler = async (res: Response) => {
  const content = await res.json();
  return content.length ? JSON.parse(content) : null;
};

export const defaultStatusValidator = (res: Response) => {
  if (res.status >= 200 && res.status < 300) {
    return true;
  } else {
    return false;
  }
};

export type NotificationType = "info" | "warning" | "success" | "error";

export const notifification = (type: NotificationType, message: string) => {
  return toast[type](message, {
    position: "top-right",
    autoClose: 5000,
    hideProgressBar: true,
    closeOnClick: false,
    pauseOnHover: true,
    draggable: false,
    progress: undefined,
    theme: "colored",
    transition: Bounce,
  });
};

/**
 * Given a bot, return the quote asset
 * This saves Binance API calls
 * @param bot
 * @returns
 */
export const getQuoteAsset = (bot: Bot, balance_to_use?: string) => {
  balance_to_use = balance_to_use || bot.fiat;
  return bot.pair.replace(balance_to_use, "");
};

// Filter by base asset (balance_to_use) provided by autotrade settings
// This is done in the front-end because it doesn't matter in the back-end, we always get the full list of symbols
export const filterSymbolByBaseAsset = (
  options: string[],
  baseAsset: string,
): string[] => {
  return options.filter((item) => item.endsWith(baseAsset));
};
