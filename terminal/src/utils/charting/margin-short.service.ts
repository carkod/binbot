import { type Bot } from "../../features/bots/botInitialState";
import { BotStatus } from "../enums";
import { dealColors } from "../../utils/charting/index";
import type { OrderLine } from "./index.d";
import { getQuoteAsset } from "../api";

export default function marginTrading(
  bot: Bot,
  currentPrice: number
): OrderLine[] {
  const quoteAsset = getQuoteAsset(bot);
  let totalOrderLines: OrderLine[] = [];
  const qtyText = bot.deal ? String(bot.deal.opening_qty) : "";
  const price =
    bot.deal?.opening_price || currentPrice || bot.deal.current_price;

  if (bot.base_order_size > 0 && currentPrice) {
    if (bot.deal.closing_price > 0) {
      // Completed bot
      totalOrderLines.push({
        id: "base_order",
        text: "Base (Margin sell)",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? `${bot.deal.opening_qty} ${quoteAsset}`
              : ""
          }`,
        ],
        quantity: `${qtyText} ${quoteAsset}`,
        price: bot.deal.opening_price,
        color: dealColors.base_order,
      });
    } else {
      // if no closing_price
      // bot inactive: currentPrice, bot active: opening_price
      totalOrderLines.push({
        id: "base_order",
        text: "Base (Margin sell)",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? `${bot.deal.opening_qty} ${quoteAsset}`
              : ""
          }`,
        ],
        quantity: `${qtyText} ${quoteAsset}`,
        price: price,
        color: dealColors.base_order,
      });
    }

    if (bot.trailling && bot.status === BotStatus.ACTIVE) {
      if (bot.deal.trailling_profit_price > 0) {
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trail profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.trailling_profit_price,
          color: dealColors.trailling_profit,
        });
      }

      if (bot.deal.trailling_stop_loss_price > 0) {
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.trailling_stop_loss_price,
          color: dealColors.take_profit,
        });
      }
    } else if (
      bot.status === BotStatus.COMPLETED &&
      bot.deal.closing_price > 0
    ) {
      // completed bot
      totalOrderLines.push({
        id: "trailling_profit",
        text: `Trail profit ${bot.trailling_profit}%`,
        tooltip: [bot.status, " Breakpoint to increase Take profit"],
        quantity: `${qtyText} ${quoteAsset}`,
        price: bot.deal.trailling_profit_price,
        color: dealColors.trailling_profit,
        lineStyle: 2,
      });
      totalOrderLines.push({
        id: "trailling_stop_loss",
        text: `Trailling stop loss -${bot.trailling_deviation}%`,
        tooltip: [bot.status, " Sell order when prices drop here"],
        quantity: `${bot.deal.opening_qty || bot.base_order_size} ${quoteAsset}`,
        price: bot.deal.trailling_stop_loss_price,
        color: dealColors.take_profit,
      });
    } else {
      // Inactive bot
      const price =
        bot.deal?.opening_price || currentPrice || bot.deal.current_price;
      const traillingProfitPrice = price * (1 - bot.trailling_profit / 100);
      if (bot.deal.trailling_profit_price > 0) {
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Take profit (trailling) ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal?.trailling_profit_price || traillingProfitPrice,
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
      }

      if (bot.deal.trailling_stop_loss_price > 0) {
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.deal.opening_qty || bot.base_order_size} ${quoteAsset}`,
          price:
            bot.deal?.trailling_profit_price ||
            traillingProfitPrice * (1 + bot.trailling_deviation / 100),
          color: dealColors.take_profit,
        });
      }
    }
  } else {
    if (bot.status === BotStatus.COMPLETED && bot.deal.take_profit_price > 0) {
      // No trailling take profit
      const price = currentPrice * (1 + bot.take_profit / 100);
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin)`,
        tooltip: [bot.status, " Buy back Order "],
        quantity: `${qtyText} ${quoteAsset}`,
        price: bot.deal.take_profit_price || price,
        color: dealColors.take_profit,
      });
    } else if (bot.status === BotStatus.INACTIVE) {
      // Inactive bot
      const price = currentPrice * (1 + bot.take_profit / 100);
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin)`,
        tooltip: [bot.status, " Buy back Order "],
        quantity: `${qtyText} ${quoteAsset}`,
        price: price,
        color: dealColors.take_profit,
      });
    }
  }

  if (bot.stop_loss > 0) {
    const stopLossPrice =
      bot.deal.stop_loss_price || currentPrice * (1 + bot.stop_loss / 100);
    totalOrderLines.push({
      id: "stop_loss",
      text: `Stop Loss ${bot.stop_loss}%`,
      tooltip: [bot.status, " Buy back order "],
      quantity: `${qtyText} ${quoteAsset}`,
      price: stopLossPrice, // buy_profit * take_profit%
      color: "red",
    });
  }

  return totalOrderLines;
}
