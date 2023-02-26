import moment from "moment";
import { checkValue, intervalOptions } from "../../validations";
import { FILTER_BY_MONTH, FILTER_BY_WEEK } from "../constants";

/**
 * This file contains redux state
 * that is shared between bots views
 * at the time of writing: bots and paper trading (test bots)
 */

// The initial state of the App
export const bot = {
  id: null,
  status: "inactive",
  balance_available: "0",
  balance_available_asset: "",
  balanceAvailableError: false,
  balanceUsageError: false,
  balance_size_to_use: 0, // Centralized
  base_order_size: "",
  baseOrderSizeError: false,
  balance_to_use: "USDT",
  bot_profit: 0,
  mode: "manual",
  max_so_count: "0",
  maxSOCountError: false,
  name: "Default bot",
  nameError: false,
  pair: "",
  price_deviation_so: "0.63",
  priceDevSoError: false,
  so_size: "0",
  soSizeError: false,
  take_profit: "3",
  takeProfitError: false,
  trailling: "false",
  trailling_deviation: "0.63",
  traillingDeviationError: false,
  formIsValid: true,
  candlestick_interval: intervalOptions[3],
  deal: {},
  orders: [],
  quoteAsset: "",
  baseAsset: "",
  stop_loss: 0,
  stopLossError: false,
  safety_orders: [],
  addAllError: "",
  cooldown: 0,
  strategy: "long",
  marginShortError: null,
  short_buy_price: 0,
  short_sell_price: 0,
};

export function setFilterByWeek() {
  return {
    type: FILTER_BY_WEEK,
  };
}

export function setFilterByMonthState() {
  return {
    type: FILTER_BY_MONTH,
  };
}

export function getProfit(base_price, current_price, strategy = "long") {
  if (!checkValue(base_price) && !checkValue(current_price)) {
    let percent =
      ((parseFloat(current_price) - parseFloat(base_price)) /
        parseFloat(base_price)) *
      100;
    if (strategy === "margin_short") {
      percent = percent * -1;
    }
    return percent.toFixed(2);
  }
  return 0;
}

/**
 * This function calculates the profit (not including commissions/fees)
 * for a single bot, namely the BotForm and TestBotForm components
 * by using input data from that individual bot as opposed to computeTotalProfit
 * function which uses an accumulator function to aggregate all profits of all bots
 *
 *
 * @param { BotSchema } bot
 * @param { number } realTimeCurrPrice
 * @returns { number }
 */
export function computeSingleBotProfit(bot, realTimeCurrPrice = null) {
  if (bot.deal && bot.base_order_size) {
    if (bot.deal.buy_price > 0) {
      const currentPrice = bot.deal.sell_price
        ? bot.deal.sell_price
        : realTimeCurrPrice || bot.deal.current_price;
      const buyPrice = bot.deal.buy_price;
      let profitChange = ((currentPrice - buyPrice) / buyPrice) * 100;
      return +profitChange.toFixed(2);
    } else if (bot.deal.margin_short_sell_price > 0) {
      // Completed margin short
      if (bot.deal.margin_short_buy_back_price > 0) {
        const currentPrice = bot.deal.margin_short_buy_back_price;
        const marginSellPrice = bot.deal.margin_short_sell_price;
        let profitChange =
          parseFloat(
            ((currentPrice - marginSellPrice) / marginSellPrice) * 100
          ) * -1;
        return +profitChange.toFixed(2);
      } else {
        const currentPrice =
          bot.deal.margin_short_buy_back_price > 0
            ? bot.deal.margin_short_buy_back_price
            : realTimeCurrPrice || bot.deal.current_price;
        if (currentPrice === 0) {
          return 0;
        }
        const marginSellPrice = bot.deal.margin_short_sell_price;
        let profitChange =
          parseFloat(
            ((currentPrice - marginSellPrice) / marginSellPrice) * 100
          ) * -1;
        return +profitChange.toFixed(2);
      }
    } else {
      return 0;
    }
  }
}

export function computeTotalProfit(bots) {
  let currTotalProfit = 0;
  const totalProfit = bots
    .map((bot) => bot.deal)
    .reduce((accumulator, currBot) => {
      if (
        currBot &&
        !checkValue(currBot.take_profit_price) &&
        parseFloat(currBot.take_profit_price) > 0
      ) {
        if (currBot.buy_price === 0) {
          currTotalProfit = 0;
        } else if (currBot.deal?.sell_price) {
          currTotalProfit = getProfit(currBot.buy_price, currBot.sell_price);
        } else {
          currTotalProfit = getProfit(
            currBot.buy_price,
            currBot.take_profit_price
          );
        }
      }
      return parseFloat(accumulator) + parseFloat(currTotalProfit);
    }, 0);
  return totalProfit.toFixed(2);
}

export function weekAgo() {
  const today = new Date();
  const lastWeek = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate() - 7
  );
  return lastWeek.getTime();
}

export function botDuration(start, end) {
  const startTime = moment(start);
  const endTime = moment(end);
  const duration = moment.duration(endTime.diff(startTime));

  let days = Math.floor(duration.asDays());
  duration.subtract(moment.duration(days, "days"));

  let hours = duration.hours();
  duration.subtract(moment.duration(hours, "hours"));

  let minutes = duration.minutes();
  duration.subtract(moment.duration(minutes, "minutes"));

  const seconds = duration.seconds();
  let dateStringify = `${seconds}s`;

  if (minutes > 0) {
    dateStringify = `${minutes}m ${dateStringify}`;
  }
  if (hours > 0) {
    dateStringify = `${hours}h ${dateStringify}`;
  }
  if (days > 0) {
    dateStringify = `${days}d ${dateStringify}`;
  }

  return dateStringify;
}

export async function checkIsolatedMargin(symbol) {
  const url = new URL(`https://api.binance.com/api/v3/exchangeInfo?symbol=${symbol}`)
  const request = await fetch(url);
  const data = await request.json();
  let check = false;
  data.symbols[0].permissions.forEach(element => {
    if (element.includes("TRD_GRP_")) {
      check = true;
      return check;
    }
  });
  return check;
}
