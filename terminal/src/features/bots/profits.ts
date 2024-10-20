import { roundDecimals } from "../../utils/math"
import { Bot } from "./botInitialState"

export function getProfit(base_price, current_price, strategy = "long") {
  if (base_price && current_price) {
    let percent =
      ((parseFloat(current_price) - parseFloat(base_price)) /
        parseFloat(base_price)) *
      100
    if (strategy === "margin_short") {
      percent = percent * -1
    }
    return parseFloat(percent.toFixed(2))
  }
  return 0
}

/**
 * Calculate interests based on hourly interest rate
 * @param {bot} bot object
 * @returns {float}
 */
function getInterestsShortMargin(bot) {
  let closeTimestamp = bot.deal.margin_short_buy_back_timestamp
  if (closeTimestamp === 0) {
    closeTimestamp = new Date().getTime()
  }
  const timeDelta = closeTimestamp - bot.deal.margin_short_sell_timestamp
  const durationHours = timeDelta / 1000 / 3600
  const interests = parseFloat(bot.deal.hourly_interest_rate) * durationHours
  const closeTotal = bot.deal.margin_short_buy_back_price
  const openTotal = bot.deal.margin_short_sell_price
  return {
    interests: interests,
    openTotal: openTotal,
    closeTotal: closeTotal,
  }
}

/**
 * This function calculates the profit (not including commissions/fees)
 * for a single bot, namely the BotForm and TestBotForm components
 * by using input data from that individual bot as opposed to computeTotalProfit
 * function which uses an accumulator function to aggregate all profits of all bots
 *
 * @param { BotSchema } bot
 * @param { number } realTimeCurrPrice
 * @returns { number }
 */
export function computeSingleBotProfit(bot: Bot, realTimeCurrPrice: number | null = null) {
  if (bot.deal && bot.base_order_size) {
    if (bot.deal.buy_price > 0) {
      const currentPrice = bot.deal.sell_price
        ? bot.deal.sell_price
        : realTimeCurrPrice || bot.deal.current_price
      const buyPrice = bot.deal.buy_price
      let profitChange = ((currentPrice - buyPrice) / buyPrice) * 100
      if (currentPrice === 0) {
        profitChange = 0
      }
      return +profitChange.toFixed(2)
    } else if (bot.deal.margin_short_sell_price > 0) {
      // Completed margin short
      if (bot.deal.margin_short_buy_back_price > 0) {
        const { interests, openTotal, closeTotal } =
          getInterestsShortMargin(bot)
        let profitChange =
          ((openTotal - closeTotal) / openTotal - interests) * 100
        return roundDecimals(profitChange, 2)
      } else {
        // Not completed margin_sho
        const closePrice =
          bot.deal.margin_short_buy_back_price > 0
            ? bot.deal.margin_short_buy_back_price
            : realTimeCurrPrice || bot.deal.current_price
        if (closePrice === 0) {
          return 0
        }
        const { interests, openTotal } = getInterestsShortMargin(bot)
        let profitChange =
          ((openTotal - closePrice) / openTotal - interests) * 100
        return roundDecimals(profitChange, 2)
      }
    } else {
      return 0
    }
  } else {
    return 0
  }
}

export function computeTotalProfit(bots) {
  let currTotalProfit: number = 0
  const totalProfit = bots
    .map(bot => bot)
    .reduce((accumulator, bot) => {
      if (
        bot?.deal?.take_profit_price &&
        parseFloat(bot?.deal?.take_profit_price) > 0
      ) {
        let enterPositionPrice = 0
        let exitPositionPrice = bot.deal.current_price

        if (bot.deal.buy_price > 0) {
          enterPositionPrice = bot.deal.buy_price
        }
        if (bot.deal.margin_short_sell_price > 0) {
          enterPositionPrice = bot.deal.margin_short_sell_price
        }
        if (bot.deal.sell_price > 0) {
          exitPositionPrice = bot.deal.sell_price
        }
        if (bot.deal.margin_short_buy_back_price > 0) {
          exitPositionPrice = bot.deal.margin_short_buy_back_price
        }

        if (exitPositionPrice === 0 || enterPositionPrice === 0) {
          currTotalProfit = 0
        } else {
          currTotalProfit = getProfit(
            enterPositionPrice,
            exitPositionPrice,
            bot.strategy,
          )
        }
      }
      return parseFloat(accumulator) + currTotalProfit
    }, 0)
  return roundDecimals(totalProfit, 2)
}

export const getNetProfit = bot => {
  // current price if bot is active
  // sell price if bot is completed
  let netProfit = computeSingleBotProfit(bot)
  if (!netProfit) netProfit = 0
  return netProfit
}
