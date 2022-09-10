export function createNewOrderLines(bot, currentPrice) {
  let totalOrderLines = [];
  if (bot.base_order_size && currentPrice) {
    totalOrderLines.push({
      id: "base_order",
      text: "Base",
      tooltip: [bot.status, " Buy Order"],
      quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
      price: currentPrice,
      color: "#1f77d0",
    });
    if (bot.safety_orders && bot.safety_orders.length > 0) {
      let safetyOrderLines = [];
      bot.safety_orders.forEach((element) => {
        safetyOrderLines.push({
          id: element.name,
          text: element.name,
          tooltip: [bot.status, " Buy order when drops here"],
          quantity: `${element.so_size} ${bot.quoteAsset}`,
          price: element.buy_price,
          color: "#ffa534",
        });
      });
      totalOrderLines = totalOrderLines.concat(safetyOrderLines);
    }
    if (bot.take_profit && bot.trailling === "true") {
      const takeProfitPrice =
        currentPrice * (1 + parseFloat(bot.take_profit) / 100);
      totalOrderLines.push({
        id: "trailling_profit",
        text: `Trailling profit ${bot.take_profit}%`,
        tooltip: [bot.status, " Breakpoint to increase Take profit"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: takeProfitPrice, // take_profit / trailling_profit
        color: "#9368e9",
      });
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit -${bot.trailling_deviation}%`,
        tooltip: [bot.status, " Sell order when prices drop here"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price:
          takeProfitPrice -
          takeProfitPrice * parseFloat(bot.trailling_deviation / 100), // take_profit / trailling_profit
        color: "#87cb16",
      });
    } else if (bot.take_profit) {
      totalOrderLines.push({
        id: "take_profit",
        text: `Take profit ${bot.take_profit}%`,
        tooltip: [bot.status, " Sell Order"],
        quantity: `${bot.base_order_size} ${bot.quoteAsset}`,
        price: currentPrice * (1 + parseFloat(bot.take_profit) / 100), // buy_profit * take_profit%
        color: "#53c887",
      });
    }
  }
	return totalOrderLines
}
