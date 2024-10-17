import { type Bot } from "../../features/bots/botInitialState"
import { BotStatus } from "../enums"
import { dealColors } from "../../utils/charting/index"
import type { OrderLine } from "./index.d"

export default function marginTrading(
  bot: Bot,
  currentPrice: number,
): OrderLine[] {
  let totalOrderLines: OrderLine[] = []
  const parsedCurrentPrice = currentPrice
  const quoteAsset = bot.pair.replace(bot.balance_to_use, "")

  if (
    bot.deal.margin_short_buy_back_price &&
    bot.deal.margin_short_buy_back_price > 0
  ) {
    totalOrderLines.push({
      id: "base_order",
      text: "Base (Margin sell)",
      tooltip: [
        bot.status,
        `${
          bot.deal.buy_total_qty && bot.deal.buy_total_qty > 0
            ? bot.deal.buy_total_qty + quoteAsset + "(Avg total)"
            : ""
        }`,
      ],
      quantity: `${bot.base_order_size} ${quoteAsset}`,
      price: parseFloat(bot.deal.margin_short_sell_price?.toString() || "0"),
      color: dealColors.base_order,
    })

    if (bot.trailling) {
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit (trailling) -${bot.trailling_deviation}%`,
        tooltip: [bot.status, " Bot closed here at profit"],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: bot.deal.margin_short_buy_back_price,
        color: dealColors.take_profit,
      })
    } else {
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin buy)`,
        tooltip: [bot.status, " Margin buy"],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: bot.deal.buy_back_price || 0, // buy_profit * take_profit%
        color: dealColors.take_profit,
      })
    }
  } else {
    if (bot.trailling) {
      if (bot.status === BotStatus.ACTIVE) {
        if (
          bot.deal.trailling_stop_loss_price &&
          bot.deal.trailling_stop_loss_price > 0
        ) {
          totalOrderLines.push({
            id: "trailling_profit",
            text: `Take profit (trailling) ${bot.take_profit}%`,
            tooltip: [bot.status, " Trace upward profit"],
            quantity: `${bot.base_order_size} ${quoteAsset}`,
            price:
              bot.deal.trailling_profit_price ||
              bot.deal.take_profit_price ||
              0, // take_profit / trailling_profit
            color: dealColors.trailling_profit,
          })
          totalOrderLines.push({
            id: "trailling_stop_loss",
            text: `Trailling stop loss -${bot.trailling_deviation}%`,
            tooltip: [bot.status, " Sell order when prices drop here"],
            quantity: `${bot.base_order_size} ${quoteAsset}`,
            price: bot.deal.trailling_stop_loss_price, // take_profit / trailling_profit
            color: dealColors.take_profit,
          })
        } else {
          const price =
            bot.deal.margin_short_sell_price &&
            bot.deal.margin_short_sell_price > 0
              ? bot.deal.margin_short_sell_price
              : parsedCurrentPrice
          totalOrderLines.push({
            id: "take_profit",
            text: `Take profit ${bot.take_profit}% (Margin)`,
            tooltip: [bot.status, " Sell Order "],
            quantity: `${bot.base_order_size} ${quoteAsset}`,
            price:
              price - (price * parseFloat(bot.take_profit.toString())) / 100, // buy_profit * take_profit%
            color: dealColors.take_profit,
          })
        }
      } else {
        const trailling_profit =
          parsedCurrentPrice - parsedCurrentPrice * (bot.take_profit / 100)
        const trailling_stop_loss_price =
          trailling_profit - trailling_profit * (bot.trailling_deviation / 100)

        totalOrderLines.push({
          id: "trailling_profit",
          text: `Take profit (trailling) ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: trailling_profit, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        })
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.buy_total_qty || bot.base_order_size} ${quoteAsset}`,
          price: trailling_stop_loss_price,
          color: dealColors.take_profit,
        })
      }
    } else {
      const price =
        bot.deal.margin_short_sell_price && bot.deal.margin_short_sell_price > 0
          ? bot.deal.margin_short_sell_price
          : parsedCurrentPrice
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin)`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: price - (price * parseFloat(bot.take_profit.toString())) / 100, // buy_profit * take_profit%
        color: dealColors.take_profit,
      })
    }
  }

  if (bot.stop_loss && bot.stop_loss > 0) {
    let stopLossPrice = 0
    if (bot.deal.stop_loss_price) {
      stopLossPrice = bot.deal.stop_loss_price
    } else {
      stopLossPrice = parsedCurrentPrice * (1 + bot.stop_loss / 100)
    }
    totalOrderLines.push({
      id: "stop_loss",
      text: `Stop Loss ${bot.stop_loss}%`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${quoteAsset}`,
      price: stopLossPrice, // buy_profit * take_profit%
      color: "red",
    })
  }

  const price =
    bot.deal.margin_short_sell_price && bot.deal.margin_short_sell_price > 0
      ? bot.deal.margin_short_sell_price
      : parsedCurrentPrice
  totalOrderLines.push({
    id: "base_order",
    text: "Base",
    tooltip: [
      bot.status,
      `${
        bot.deal.buy_total_qty && bot.deal.buy_total_qty > 0
          ? bot.deal.buy_total_qty + quoteAsset + "(Avg total)"
          : ""
      }`,
    ],
    quantity: `${bot.base_order_size} ${quoteAsset}`,
    price: parseFloat(price.toString()),
    color: dealColors.base_order,
  })

  return totalOrderLines
}
