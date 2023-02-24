import spotTrading from "./spot-strategy.service";
import marginTrading from "./margin-short.service";

const dealColors = {
  base_order: "#1f77d0",
  trailling_profit: "#9368e9",
  take_profit: "#87cb16",
  safety_order: "#ffa534",
};

function matchTsToTimescale(ts) {
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

export function updateOrderLines(bot, currentPrice) {
  /**
   * Updates orderlines for the chart
   * @param bot {object: Bot} required.
   * @param currentPrice {string}. If inactive, use chart current price, if bot active, use buy_price
   */
  let totalOrderLines = [];
  if (bot.strategy === "margin_short") {
    totalOrderLines = marginTrading(bot, currentPrice);
  } else {
    totalOrderLines = spotTrading(bot, currentPrice);
  }

  return totalOrderLines;
}

export function updateTimescaleMarks(bot) {
  let totalTimescaleMarks = [];
  let color = "blue";
  let label = "B";
  if (bot.orders && bot.orders.length > 0) {
    bot.orders.forEach((order) => {
      // If base_order and margin_short
      if (bot.strategy === "margin_short") {
        label = "S";  
      }
      if (
        order.deal_type === "take_profit" ||
        order.deal_type === "stop_loss"
      ) {
        color = dealColors.take_profit;
        if (bot.strategy === "margin_short") {
          label = "B";  
        }
        label = "S";
      }
      if (order.deal_type === "trailling_profit") {
        color = dealColors.trailling_profit;
      }
      if (order.deal_type === "trailling_stop_loss") {
        color = dealColors.take_profit;
        label = "S";
      }
      if (order.deal_type.startsWith("so")) {
        color = dealColors.safety_order;
      }
      const timescaleMark = {
        id: order.order_id,
        label: label,
        tooltip: [
          `${order.deal_type}`,
          ` ${order.price} ${bot.baseAsset} / ${order.qty} ${bot.quoteAsset}`,
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
