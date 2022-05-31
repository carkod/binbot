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
  _id: null,
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
  safety_orders: {},
  addAllError: "",
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

export function getProfit(base_price, current_price) {
  if (!checkValue(base_price) && !checkValue(current_price)) {
    const percent =
      ((parseFloat(current_price) - parseFloat(base_price)) /
        parseFloat(base_price)) *
      100;
    return percent.toFixed(2);
  }
  return 0;
}

export function computeTotalProfit(bots) {
  const totalProfit = bots
    .map((bot) => bot.deal)
    .reduce((accumulator, currBot) => {
      let currTotalProfit = getProfit(currBot.buy_price, currBot.current_price);
      if (currBot.status === "completed" && !checkValue(currBot.sell_price)) {
        currTotalProfit = this.getProfit(currBot.buy_price, currBot.sell_price);
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
  const duration = moment.duration(startTime.diff(endTime));

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
