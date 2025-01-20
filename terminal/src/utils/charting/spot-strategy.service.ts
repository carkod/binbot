import { type OrderLine } from "./index.d";
import { type Bot } from "../../features/bots/botInitialState";
import { dealColors } from "../../utils/charting/index";
import { getQuoteAsset } from "../api";
import { BotStatus } from "../enums";

export default function spotTrading(
  bot: Bot,
  currentPrice: number,
): OrderLine[] {
  const quoteAsset = getQuoteAsset(bot);
  let totalOrderLines: OrderLine[] = [];
  if (
    bot.deal.opening_price &&
    bot.deal.opening_price > 0 &&
    bot.status === BotStatus.ACTIVE
  ) {
    currentPrice = bot.deal.opening_price;
  }

  if (bot.base_order_size && currentPrice) {
    if (bot.deal.closing_price && bot.deal.closing_price > 0) {
      // If there is sell_price, it means it's completed
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? bot.deal.opening_qty + quoteAsset + "(Avg total)"
              : ""
          }`,
        ],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: bot.deal.opening_price || 0,
        color: dealColors.base_order,
      });
    } else {
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? bot.deal.opening_qty + quoteAsset + "(Avg total)"
              : ""
          }`,
        ],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: currentPrice,
        color: dealColors.base_order,
      });
    }

    if (
      bot.take_profit &&
      bot.trailling &&
      bot.deal.trailling_stop_loss_price &&
      bot.deal.trailling_stop_loss_price > 0
    ) {
      // Bot is sold and completed
      if (bot.status === "completed" && bot.deal.closing_price) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell when prices drop to here"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.closing_price,
          color: dealColors.take_profit,
        });
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.closing_price * (1 + bot.take_profit / 100), // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
      } else if (
        bot.deal.opening_price &&
        bot.deal.take_profit_price &&
        bot.status === "active"
      ) {
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.trailling_profit_price || bot.deal.take_profit_price, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
        });
        totalOrderLines.push({
          id: "take_profit",
          text: `Trailling profit ${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.trailling_stop_loss_price, // take_profit / trailling_profit
          color: dealColors.take_profit,
        });
      } else {
        // If trailling moved the orderlines
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.trailling_profit_price || bot.deal.take_profit_price, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.deal.opening_qty || bot.base_order_size} ${
            quoteAsset
          }`,
          price: bot.deal.trailling_stop_loss_price,
          color: dealColors.take_profit,
        });
      }
    } else if (bot.take_profit) {
      // No trailling, just normal take_profit
      if (bot.status === "completed" && bot.deal.opening_price) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.opening_price * (1 + bot.take_profit / 100), // buy_profit * take_profit%
          color: dealColors.take_profit,
        });
      } else {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: currentPrice * (1 + bot.take_profit / 100), // buy_profit * take_profit%
          color: dealColors.take_profit,
        });
      }
    }
    if (bot.stop_loss && bot.stop_loss > 0) {
      let stopLossPrice = 0;
      if (bot.deal.opening_price) {
        stopLossPrice =
          bot.deal.opening_price -
          bot.deal.opening_price * (bot.stop_loss / 100);
      } else {
        stopLossPrice = currentPrice - currentPrice * (bot.stop_loss / 100);
      }
      // Stop loss

      totalOrderLines.push({
        id: "stop_loss",
        text: `Stop Loss ${bot.stop_loss}%`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: stopLossPrice, // buy_profit * take_profit%
        color: "red",
      });
    }
  }
  return totalOrderLines;
}
