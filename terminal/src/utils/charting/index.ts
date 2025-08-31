import spotTrading from "./spot-strategy.service";
import marginTrading from "./margin-short.service";
import { type Bot } from "../../features/bots/botInitialState";
import { type TimescaleMark } from "./index.d";
import { BotStrategy, DealType } from "../enums";

const dealColors = {
  base_order: "#1f77d0",
  trailling_profit: "#9368e9",
  take_profit: "#87cb16",
  safety_order: "#ffa534",
};

function matchTsToTimescale(ts: string): number {
  /**
   * Internal utility function to match timestamp to timescale
   * If this is NOT matched, the chart will not show the mark
   * This time is matched to closest hour (assuming interval hour)
   */

  const date = new Date(parseFloat(ts));
  date.setMinutes(0);
  date.setSeconds(0);
  date.setMilliseconds(0);
  const newTs = date.getTime();
  return newTs / 1000;
}

export function updateOrderLines(bot: Bot, currentPrice: number): any[] {
  /**
   * Updates orderlines for the chart
   * @param bot {object: Bot} required.
   * @param currentPrice {number}. If inactive, use chart current price, if bot active, use buy_price
   */
  let totalOrderLines = [];
  if (bot.strategy === BotStrategy.MARGIN_SHORT) {
    totalOrderLines = marginTrading(bot, currentPrice);
  } else {
    totalOrderLines = spotTrading(bot, currentPrice);
  }

  return totalOrderLines;
}

export function updateTimescaleMarks(bot: Bot): TimescaleMark[] {
  let totalTimescaleMarks: TimescaleMark[] = [];
  let color = "blue";
  let label = "B";
  const quoteAsset = bot.quote_asset;
  if (bot.orders && bot.orders.length > 0) {
    bot.orders.forEach((order) => {
      // If base_order and margin_short
      if (bot.strategy === BotStrategy.MARGIN_SHORT) {
        label = "S";
      }
      if (
        order.deal_type === DealType.TAKE_PROFIT ||
        order.deal_type === DealType.STOP_LOSS
      ) {
        color = dealColors.take_profit;
        if (bot.strategy === BotStrategy.MARGIN_SHORT) {
          label = "B";
        }
        label = "S";
      }
      if (order.deal_type === DealType.TRAILLING_PROFIT) {
        color = dealColors.trailling_profit;
      }
      if (order.deal_type === DealType.TRAILLING_STOP_LOSS) {
        color = dealColors.take_profit;
        label = "S";
      }
      if (order.deal_type.startsWith("so")) {
        color = dealColors.safety_order;
      }
      const timescaleMark: TimescaleMark = {
        id: order.order_id,
        label: label,
        tooltip: [
          `${order.deal_type}`,
          ` ${order.price} ${bot.fiat} / ${order.qty} ${quoteAsset}`,
        ],
        time: matchTsToTimescale(order.timestamp),
        color: color,
      };

      // Avoid object not extensible error
      // Since tradingview library requires this, it can be an exception to immutable state
      totalTimescaleMarks.push(timescaleMark);
    });
  }
  return totalTimescaleMarks;
}

export { dealColors };
