import { type OrderLine } from "./index.d";
import { type Bot } from "../../features/bots/botInitialState";
import { dealColors } from "../../utils/charting/index";
import { getQuoteAsset } from "../api";

export default function spotTrading(
  bot: Bot,
  currentPrice: number,
): OrderLine[] {
  const quoteAsset = getQuoteAsset(bot);
  let totalOrderLines: OrderLine[] = [];
  if (bot.deal.buy_price && bot.deal.buy_price > 0 && bot.status === "active") {
    currentPrice = bot.deal.buy_price;
  }

  // short strategy
  if (bot.short_buy_price && bot.short_buy_price > 0) {
    totalOrderLines.push({
      id: "short_buy_price",
      text: "Short buy price",
      tooltip: [` Price: ${bot.short_buy_price}`],
      quantity: `${bot.base_order_size} ${quoteAsset}`,
      price: bot.short_buy_price,
      color: dealColors.trailling_profit,
    });
  }

  if (bot.short_sell_price && bot.short_sell_price > 0) {
    totalOrderLines.push({
      id: "short_sell_price",
      text: "Short sell price",
      tooltip: [` Price: ${bot.short_sell_price}`],
      quantity: `${bot.base_order_size} ${quoteAsset}`,
      price: bot.short_sell_price,
      color: dealColors.trailling_profit,
    });
  }

  if (bot.base_order_size && currentPrice) {
    if (bot.deal.original_buy_price && bot.deal.original_buy_price > 0) {
      totalOrderLines.push({
        id: "original_buy_price",
        text: "Original buy price",
        tooltip: [bot.status, " Original buy price before SO triggered"],
        quantity: `${bot.base_order_size} ${quoteAsset}`,
        price: bot.deal.original_buy_price,
        color: dealColors.base_order,
      });
    }

    if (bot.deal.sell_price && bot.deal.sell_price > 0) {
      // If there is sell_price, it means it's completed
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
        price: bot.deal.buy_price || 0,
        color: dealColors.base_order,
      });
    } else {
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
      if (bot.status === "completed" && bot.deal.sell_price) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell when prices drop to here"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.sell_price,
          color: dealColors.take_profit,
        });
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.sell_price * (1 + bot.take_profit / 100), // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
      } else if (
        bot.deal.buy_price &&
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
          quantity: `${bot.buy_total_qty || bot.base_order_size} ${
            quoteAsset
          }`,
          price: bot.deal.trailling_stop_loss_price,
          color: dealColors.take_profit,
        });
      }
    } else if (bot.take_profit) {
      // No trailling, just normal take_profit
      if (bot.status === "completed" && bot.deal.buy_price) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${bot.base_order_size} ${quoteAsset}`,
          price: bot.deal.buy_price * (1 + bot.take_profit / 100), // buy_profit * take_profit%
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
    if (bot.safety_orders && bot.safety_orders.length > 0) {
      let safetyOrderLines: OrderLine[] = [];
      bot.safety_orders.forEach((element) => {
        if (element.status === undefined || element.status === 0) {
          safetyOrderLines.push({
            id: element.name,
            text: element.name,
            tooltip: [bot.status, " Buy order when drops here"],
            quantity: `${element.so_size} ${quoteAsset}`,
            price: element.buy_price,
            color: dealColors.safety_order,
            lineStyle: 2,
          });
        }
      });
      totalOrderLines = totalOrderLines.concat(safetyOrderLines);
    }

    if (bot.stop_loss && bot.stop_loss > 0) {
      let stopLossPrice = 0;
      if (bot.deal.buy_price) {
        stopLossPrice =
          bot.deal.buy_price - bot.deal.buy_price * (bot.stop_loss / 100);
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
