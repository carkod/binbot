import { dealColors } from "./charting.service";

export default function marginTrading(bot, currentPrice) {
  let totalOrderLines = [];
  currentPrice = parseFloat(currentPrice)
  if (bot.deal.buy_back_price && bot.deal.buy_back_price > 0) {

    // If there is sell_price, it means it's completed
    totalOrderLines.push({
      id: "base_order",
      text: "Base (Margin sell)",
      tooltip: [
        bot.status,
        `${
          bot.deal.buy_total_qty > 0
            ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)"
            : ""
        }`,
      ],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: parseFloat(bot.deal.margin_short_sell_price),
      color: dealColors.base_order,
    });
    if (bot.trailling === "true") {
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit (trailling) -${bot.trailling_deviation}%`,
        tooltip: [bot.status, " Bot closed here at profit"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: bot.deal.margin_short_buy_back_price,
        color: dealColors.take_profit,
      });
    } else {
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin buy)`,
        tooltip: [bot.status, " Margin buy"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: bot.deal.buy_back_price, // buy_profit * take_profit%
        color: dealColors.take_profit,
      });
    }
    
  } else {

    if (bot.trailling === "trailling") {
      if (bot.status === "active" && bot.deal.trailling_stop_loss_price > 0) {
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Take profit (trailling) ${bot.take_profit}%`,
          tooltip: [bot.status, " Trace upward profit"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.trailling_profit_price || bot.deal.take_profit_price, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
        });
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: bot.deal.trailling_stop_loss_price, // take_profit / trailling_profit
          color: dealColors.take_profit,
        });
      } else {
        // If trailling moved the orderlines
        // If deal doesn't exist
        const trailling_profit = currentPrice - (currentPrice * (bot.take_profit / 100))
        const trailling_stop_loss_price = trailling_profit - (trailling_profit * (bot.trailling_deviation * 100))
        
        totalOrderLines.push({
          id: "trailling_profit",
          text: `Take profit (trailling) ${bot.take_profit}%`,
          tooltip: [bot.status, " Breakpoint to increase Take profit"],
          quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
          price: trailling_profit, // take_profit / trailling_profit
          color: dealColors.trailling_profit,
          lineStyle: 2,
        });
        totalOrderLines.push({
          id: "trailling_stop_loss",
          text: `Trailling stop loss -${bot.trailling_deviation}%`,
          tooltip: [bot.status, " Sell order when prices drop here"],
          quantity: `${bot.buy_total_qty || bot.base_order_size} ${
            bot.quoteAsset
          }`,
          price: trailling_stop_loss_price,
          color: dealColors.take_profit,
        });
      }
    } else {
      const price = bot.deal.margin_short_sell_price > 0 ? bot.deal.margin_short_sell_price : currentPrice;
      totalOrderLines.push({
        id: "base_order",
        text: "Base",
        tooltip: [
          bot.status,
          `${
            bot.deal.buy_total_qty > 0
              ? bot.deal.buy_total_qty + bot.quoteAsset + "(Avg total)"
              : ""
          }`,
        ],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: parseFloat(price),
        color: dealColors.base_order,
      });
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}% (Margin)`,
        tooltip: [bot.status, " Sell Order "],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: price - ( price * parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
        color: dealColors.take_profit,
      });
    }
  }

  if (bot.stop_loss && parseFloat(bot.stop_loss) > 0) {
    let stopLossPrice = 0;
    if (bot.deal.stop_loss_price) {
      stopLossPrice =
        bot.deal.stop_loss_price;
    } else {
      stopLossPrice = currentPrice * (1 + (parseFloat(bot.stop_loss) / 100));
    }
    // Stop loss
    totalOrderLines.push({
      id: "stop_loss",
      text: `Stop Loss ${bot.stop_loss}%`,
      tooltip: [bot.status, " Sell Order "],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: stopLossPrice, // buy_profit * take_profit%
      color: "red",
    });
  }

  return totalOrderLines;
}
