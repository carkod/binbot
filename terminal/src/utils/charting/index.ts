import spotTrading from "./spot-strategy.service";
import marginTrading from "./margin-short.service";
import { type Bot } from "../../features/bots/botInitialState";
import { type TimescaleMark } from "./index.d";
import { BotPosition, BotStatus, EntryMode, DealType } from "../enums";
import { matchTsToTimescale } from "../time";

const dealColors = {
  entry_price: "#e056b5",
  base_order: "#1f77d0",
  trailing_profit: "#9368e9",
  take_profit: "#87cb16",
  trailing_stop_loss: "#87cb16",
  stop_loss: "red",
  safety_order: "#ffa534",
};

export function updateOrderLines(
  bot: Bot,
  currentPrice: number,
  previewTrailingSettings = false,
  previewStopLossSettings = false,
): any[] {
  /**
   * Updates orderlines for the chart
   * @param bot {object: Bot} required.
   * @param currentPrice {number}. If inactive, use chart current price, if bot active, use buy_price
   */
  let totalOrderLines = [];
  if (bot.position === BotPosition.SHORT) {
    totalOrderLines = marginTrading(
      bot,
      currentPrice,
      previewTrailingSettings,
      previewStopLossSettings,
    );
  } else {
    totalOrderLines = spotTrading(
      bot,
      currentPrice,
      previewTrailingSettings,
      previewStopLossSettings,
    );
  }

  return totalOrderLines;
}

export function updateTimescaleMarks(bot: Bot): TimescaleMark[] {
  let totalTimescaleMarks: TimescaleMark[] = [];
  const quoteAsset = bot.quote_asset;
  if (bot.orders && bot.orders.length > 0) {
    bot.orders.forEach((order) => {
      // Skip conversion and cancelled orders
      if (
        order.deal_type === DealType.CONVERSION ||
        ["CANCELED", "CANCELLED"].includes(order.status?.toUpperCase())
      ) {
        return;
      }
      let color = dealColors.base_order;
      let label = "B";
      // If base_order and margin_short
      if (bot.position === BotPosition.SHORT) {
        label = "S";
      }
      if (order.deal_type === DealType.TAKE_PROFIT) {
        color = dealColors.take_profit;
        if (bot.position === BotPosition.SHORT) {
          label = "B";
        }
        label = "S";
      }
      if (order.deal_type === DealType.STOP_LOSS) {
        color = dealColors.stop_loss;
        label = "S";
      }
      if (order.deal_type === DealType.TRAILING_PROFIT) {
        color = dealColors.trailing_profit;
      }
      if (order.deal_type === DealType.TRAILING_STOP_LOSS) {
        color = dealColors.trailing_stop_loss;
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
  if (
    bot.entry_mode === EntryMode.CONDITIONAL_LIMIT &&
    bot.entry_price > 0 &&
    (bot.status === BotStatus.INACTIVE || bot.status === BotStatus.PENDING)
  ) {
    if (!bot.orders?.some((order) => order.deal_type === DealType.BASE_ORDER)) {
      totalTimescaleMarks.push({
        id: "conditional_entry",
        label: "E",
        tooltip: ["Conditional entry", `${bot.entry_price} ${bot.fiat}`],
        time: matchTsToTimescale(bot.created_at ?? Date.now()),
        color: dealColors.entry_price,
      });
    }
    if (bot.entry_expires_at) {
      totalTimescaleMarks.push({
        id: "conditional_entry_expiry",
        label: "X",
        tooltip: [
          "Conditional entry expires",
          new Date(bot.entry_expires_at).toLocaleString(),
        ],
        time: matchTsToTimescale(bot.entry_expires_at),
        color: dealColors.entry_price,
      });
    }
  }
  return totalTimescaleMarks;
}

export { dealColors };
