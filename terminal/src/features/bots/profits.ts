import { BotPosition } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { type Bot } from "./botInitialState";

export function getProfit(
  base_price: number,
  current_price: number,
  strategy = BotPosition.LONG,
) {
  if (base_price && current_price) {
    let percent = ((current_price - base_price) / base_price) * 100;
    if (strategy === BotPosition.SHORT) {
      percent = percent * -1;
    }
    return parseFloat(percent.toFixed(2));
  }
  return 0;
}

/**
 * This function calculates the profit (not including commissions/fees)
 * for a single bot, namely the BotForm and TestBotForm components
 * by using input data from that individual bot as opposed to computeTotalProfit
 * function which uses an accumulator function to aggregate all profits of all bots
 */
export function computeSingleBotProfit(
  bot: Bot,
  realTimeCurrPrice: number = 0,
) {
  if (!bot?.deal) {
    return 0;
  }

  const base_order_size =
    bot.deal.base_order_size && bot.deal.base_order_size > 0
      ? bot.deal.base_order_size
      : bot.fiat_order_size;

  if (base_order_size <= 0) {
    return 0;
  }

  if (bot.deal.opening_price > 0) {
    // 1. closing price, 2. real time price, 3. deal current price
    const currentPrice =
      bot.deal.closing_price > 0
        ? bot.deal.closing_price
        : realTimeCurrPrice > 0
          ? realTimeCurrPrice
          : bot.deal.current_price;
    const buyPrice = bot.deal.opening_price;
    if (currentPrice > 0) {
      const profitChange = getProfit(buyPrice, currentPrice, bot.strategy);
      return roundDecimals(profitChange, 2);
    }
    return 0;
  }

  if (bot.deal.closing_price > 0) {
    // Completed margin short
    const profitChange = getProfit(
      bot.deal.opening_price,
      bot.deal.closing_price,
      bot.strategy,
    );
    return roundDecimals(profitChange, 2);
  }

  // Not completed margin_short
  const closePrice =
    bot.deal.closing_price > 0
      ? bot.deal.closing_price
      : realTimeCurrPrice || bot.deal.current_price;

  if (closePrice === 0) {
    return 0;
  }
  const profitChange = getProfit(
    bot.deal.opening_price,
    closePrice,
    bot.strategy,
  );
  return roundDecimals(profitChange, 2);
}

export function computeTotalProfit(bots: Bot[] = []) {
  const totalProfit = bots.reduce((accumulator, bot) => {
    const openingPrice = bot?.deal?.opening_price ?? 0;
    const closingOverride = bot?.deal?.closing_price ?? 0;
    const currentPrice = bot?.deal?.current_price ?? 0;
    const closingPrice = closingOverride > 0 ? closingOverride : currentPrice;

    if (closingPrice === 0 || openingPrice === 0) {
      return accumulator;
    }

    const profit = getProfit(openingPrice, closingPrice, bot.strategy);
    return accumulator + profit;
  }, 0);
  return roundDecimals(totalProfit, 2);
}

export const getNetProfit = (bot) => {
  // current price if bot is active
  // sell price if bot is completed
  let netProfit = computeSingleBotProfit(bot);
  if (!netProfit) netProfit = 0;
  return netProfit;
};
