import { type OrderLine } from "./index.d";
import { type Bot } from "../../features/bots/botInitialState";
import { dealColors } from "../../utils/charting/index";
import { BotStatus } from "../enums";

export default function spotTrading(
  bot: Bot,
  currentPrice: number = 0,
): OrderLine[] {
  const quoteAsset = bot.quote_asset;
  let totalOrderLines: OrderLine[] = [];
  const price =
    bot.deal?.opening_price > 0 || currentPrice > 0 || bot.deal.current_price;

  if (bot.base_order_size > 0 && currentPrice) {
    const qtyText =
      bot.deal.opening_qty > 0
        ? String(bot.deal.opening_qty)
        : String(bot.base_order_size);
    if (bot.deal.closing_price > 0) {
      // If there is closing_price, it means it's completed
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty > 0
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
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.opening_qty && bot.deal.opening_qty > 0
              ? `${bot.deal.opening_qty} ${quoteAsset}`
              : ""
          }`,
        ],
        quantity: `${qtyText} ${quoteAsset}`,
        price: bot.deal.opening_price || currentPrice,
        color: dealColors.base_order,
      });
    }

    if (
      bot.trailling &&
      bot.trailling_deviation > 0 &&
      bot.trailling_profit > 0
    ) {
      // Bot is sold and completed
      if (bot.status === BotStatus.COMPLETED && bot.deal.closing_price > 0) {
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell when prices drop to here"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.closing_price,
          color: dealColors.take_profit,
        });
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.trailling_profit}%`,
          tooltip: [bot.status, " Breakpoint to move up trailling profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.closing_price, // closing_price is probably the most accurate closing position price, trailling_profit may not be the price it was sold at
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
      } else if (
        bot.deal.opening_price > 0 &&
        bot.status === BotStatus.ACTIVE
      ) {
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trail profit ${bot.trailling_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.trailling_profit_price,
          color: dealColors.trailling_profit,
        });
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss ${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.trailling_stop_loss_price,
          color: dealColors.take_profit,
        });
      } else {
        // Inactive bot
        const traillingProfitPrice =
          currentPrice * (1 + bot.trailling_profit / 100);
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.trailling_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${qtyText} ${quoteAsset}`,
          price: traillingProfitPrice,
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
          price: traillingProfitPrice * (1 - bot.trailling_deviation / 100),
          color: dealColors.take_profit,
        });
      }
    } else {
      // No trailling, just normal take_profit
      if (
        bot.status === BotStatus.COMPLETED &&
        bot.deal.take_profit_price > 0
      ) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${qtyText} ${quoteAsset}`,
          price: bot.deal.take_profit_price, // this makes sure we use the real-time price
          color: dealColors.take_profit,
        });
      } else {
        if (!bot.trailling) {
          totalOrderLines.push({
            id: "take_profit",
            text: `Take profit ${bot.take_profit}%`,
            tooltip: [bot.status, " Sell Order "],
            quantity: `${qtyText} ${quoteAsset}`,
            price: currentPrice * (1 + bot.take_profit / 100), // buy_profit * take_profit%
            color: dealColors.take_profit,
          });
        }
      }
    }

    // Stop loss remains the same in all situations
    if (bot.stop_loss > 0) {
      const stop_loss =
        bot.deal.stop_loss_price || currentPrice * (1 - bot.stop_loss / 100);
      totalOrderLines.push({
        id: "stop_loss",
        text: `Stop Loss ${bot.stop_loss}%`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${qtyText} ${quoteAsset}`,
        price: stop_loss,
        color: "red",
      });
    }
  }
  return totalOrderLines;
}
