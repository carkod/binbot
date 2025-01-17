import { roundDecimals } from "../../utils/math";
import { type Bot } from "./botInitialState";

export function getProfit(base_price, current_price, strategy = "long") {
  if (base_price && current_price) {
    let percent =
      ((parseFloat(current_price) - parseFloat(base_price)) /
        parseFloat(base_price)) *
      100;
    if (strategy === "margin_short") {
      percent = percent * -1;
    }
    return parseFloat(percent.toFixed(2));
  }
  return 0;
}

/**
 * Calculate interests based on hourly interest rate
 * @param {bot} bot object
 * @returns {float}
 */
function getInterestsShortMargin(bot) {
  let closeTimestamp = bot.deal.closing_timestamp;
  if (closeTimestamp === 0) {
    closeTimestamp = new Date().getTime();
  }
  const closeTotal = bot.deal.closing_price;
  const openTotal = bot.deal.opening_price;
  return {
    openTotal: openTotal,
    closeTotal: closeTotal,
  };
}

/**
 * This function calculates the profit (not including commissions/fees)
 * for a single bot, namely the BotForm and TestBotForm components
 * by using input data from that individual bot as opposed to computeTotalProfit
 * function which uses an accumulator function to aggregate all profits of all bots
 *
 * @param { BotModel } bot
 * @param { number } realTimeCurrPrice
 * @returns { number }
 */
export function computeSingleBotProfit(
  bot: Bot,
  realTimeCurrPrice: number | null = null
) {
  if (bot.deal && bot.base_order_size > 0) {
    if (bot.deal.opening_price > 0) {
      const currentPrice = bot.deal.closing_price
        ? bot.deal.closing_price
        : realTimeCurrPrice || bot.deal.current_price;
      const buyPrice = bot.deal.opening_price;
      let profitChange = ((currentPrice - buyPrice) / buyPrice) * 100;
      if (currentPrice === 0) {
        profitChange = 0;
      }
      return +profitChange.toFixed(2);
    } else if (bot.deal.closing_price > 0) {
      // Completed margin short
      
      let profitChange =
        ((bot.deal.opening_price - bot.deal.closing_price) / bot.deal.opening_price) * 100;
      return roundDecimals(profitChange, 2);
    } else {
      // Not completed margin_short
      const closePrice =
        bot.deal.closing_price > 0
          ? bot.deal.closing_price
          : realTimeCurrPrice || bot.deal.current_price;
      if (closePrice === 0) {
        return 0;
      }

      let profitChange =
        ((bot.deal.opening_price - bot.deal.closing_price) / bot.deal.opening_price) * 100;
      return roundDecimals(profitChange, 2);
    }
  } else {
    return 0;
  }
}

export function computeTotalProfit(bots) {
  let currTotalProfit: number = 0;
  const totalProfit = bots
    .map((bot) => bot)
    .reduce((accumulator, bot) => {
      if (
        bot?.deal?.take_profit_price &&
        parseFloat(bot?.deal?.take_profit_price) > 0
      ) {
        let enterPositionPrice = 0;
        let exitPositionPrice = bot.deal.current_price;

        if (bot.deal.opening_price > 0) {
          enterPositionPrice = bot.deal.opening_price;
        }
        if (bot.deal.closing_price > 0) {
          enterPositionPrice = bot.deal.closing_price;
        }
        if (bot.deal.closing_price > 0) {
          exitPositionPrice = bot.deal.closing_price;
        }
        if (bot.deal.closing_price > 0) {
          exitPositionPrice = bot.deal.closing_price;
        }

        if (exitPositionPrice === 0 || enterPositionPrice === 0) {
          currTotalProfit = 0;
        } else {
          currTotalProfit = getProfit(
            enterPositionPrice,
            exitPositionPrice,
            bot.strategy
          );
        }
      }
      return parseFloat(accumulator) + currTotalProfit;
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
