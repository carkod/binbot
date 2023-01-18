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
  date.setSeconds(0)
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
  if (
    bot.deal.buy_price &&
    parseFloat(bot.deal.buy_price) > 0 &&
    bot.status === "active"
  ) {
    currentPrice = bot.deal.buy_price;
  }

  // short strategy
  if (bot.short_buy_price && bot.short_buy_price > 0) {
    totalOrderLines.push({
      id: "short_buy_price",
      text: "Short buy price",
      tooltip: [` Price: ${bot.short_buy_price}`],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: parseFloat(bot.short_buy_price),
      color: dealColors.trailling_profit,
    });
  }

  if (bot.short_sell_price && bot.short_sell_price > 0) {
    totalOrderLines.push({
      id: "short_sell_price",
      text: "Short sell price",
      tooltip: [` Price: ${bot.short_sell_price}`],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: parseFloat(bot.short_sell_price),
      color: dealColors.trailling_profit,
    });
  }

  if (bot.base_order_size && currentPrice) {
    if (bot.deal.original_buy_price && bot.deal.original_buy_price > 0) {
      totalOrderLines.push({
        id: "original_buy_price",
        text: "Original buy price",
        tooltip: [bot.status, " Original buy price before SO triggered"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: parseFloat(bot.deal.original_buy_price),
        color: dealColors.base_order,
      });
    }

    if (bot.deal.sell_price && bot.deal.sell_price > 0) {
      // If there is sell_price, it means it's completed
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [bot.status, `${bot.deal.buy_total_qty > 0 ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)" : ""}`],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: parseFloat(bot.deal.buy_price),
        color: dealColors.base_order,
      });
    } else {
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [bot.status, `${bot.deal.buy_total_qty > 0 ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)" : ""}`],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: parseFloat(currentPrice),
        color: dealColors.base_order,
      });
    }
    
    if (bot.take_profit && bot.trailling === "true" && bot.deal.trailling_stop_loss_price > 0) {
      // Bot is sold and completed
      if (bot.status === "completed" && bot.deal.sell_price) {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell when prices drop to here"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.sell_price,
          color: dealColors.take_profit,
        });
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.sell_price * (1 + parseFloat(bot.take_profit) / 100), // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
      } else if (bot.deal.buy_price && bot.deal.take_profit_price && bot.status === "active") {
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.take_profit_price, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
        });
        totalOrderLines.push({
          id: "take_profit",
          text: `Trailling profit ${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.trailling_stop_loss_price, // take_profit / trailling_profit
          color: dealColors.take_profit,
        });
      } else {
        // If trailling moved the orderlines
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Trailling profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.take_profit_price, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
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
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.buy_price * (1 + parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
          color: dealColors.take_profit,
        });
      } else {
        totalOrderLines.push({
          id: "take_profit",
          text: `Take profit ${bot.take_profit}%`,
          tooltip: [bot.status, " Sell Order "],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: currentPrice * (1 + parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
          color: dealColors.take_profit,
        });
      }
    }
    if (bot.safety_orders && bot.safety_orders.length > 0) {
      let safetyOrderLines = [];
      bot.safety_orders.forEach((element) => {
        if (element.status === undefined || element.status === 0) {
          safetyOrderLines.push({
            id: element.name,
            text: element.name,
            tooltip: [bot.status, " Buy order when drops here"],
            quantity: `${element.so_size} ${bot.quoteAsset}`,
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
        stopLossPrice = bot.deal.buy_price - (bot.deal.buy_price * (bot.stop_loss / 100));
      } else {
        stopLossPrice = currentPrice - (currentPrice * (bot.stop_loss / 100));
      }
      // Stop loss
     
      totalOrderLines.push({
        id: "stop_loss",
        text: `Stop Loss ${bot.stop_loss}%`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: stopLossPrice, // buy_profit * take_profit%
        color: "red",
      })
    }
  }
  return totalOrderLines;
}

export function updateTimescaleMarks(bot) {
  let totalTimescaleMarks = [];
  let color = "blue";
  let label = "B";
  if (bot.orders && bot.orders.length > 0) {
    bot.orders.forEach((order) => {
      if (order.deal_type === "take_profit") {
        color = dealColors.take_profit;
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
        tooltip: [order.status, ` ${order.deal_type} ${order.qty}`],
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
