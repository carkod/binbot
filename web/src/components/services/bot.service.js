import { checkValue } from "../../validations";

/**
 * Generate annotations and shapes with real base_order_price
 * @param {*} data
 * @param {*} bot
 * @returns annotations, shapes
 */
export const botCandlestick = (data, bot, deal = null) => {
  let annotations = [];
  let shapes = [];
  let currentPrice, currentTime, takeProfit, takeProfitTime;

  // Match real base order price and time if active
  currentPrice = data.trace[0].close[data.trace[0].close.length - 1];
  currentTime = data.trace[0].x[data.trace[0].x.length - 1];

  // Match last order (last safety order triggered)
  takeProfit = data.trace[0].close[data.trace[0].close.length - 1];
  takeProfitTime = data.trace[0].x[data.trace[0].x.length - 1];

  // Saved current price visual
  if (!checkValue(deal)) {
    if ("current_price" in deal) {
      const currentPriceSA = {
        x: currentTime,
        y: deal.current_price,
        xref: "x",
        yref: "y",
        text: `CP`,
        font: { color: "blue" },
        showarrow: false,
        xanchor: "left",
        hovertext: deal.current_price,
      };
      const currentPriceS = {
        type: "line",
        xref: "x",
        yref: "y",
        x0: currentTime,
        y0: deal.current_price,
        x1: data.trace[0].x[195],
        y1: deal.current_price,
        line: {
          color: "blue",
          width: 12,
          dash: "dot",
        },
      };
      shapes.push(currentPriceS);
      annotations.push(currentPriceSA);
    }
  }

  if (bot.orders.length > 0) {
    const baseOrder = bot.orders.find((x) => x.deal_type === "base_order");
    if (!checkValue(baseOrder)) {
      currentPrice = baseOrder.price;
    }
  }

  // Base order Annotation
  const baseOrderA = {
    x: currentTime,
    y: currentPrice,
    xref: "x",
    yref: "y",
    text: `Base order`,
    font: { color: "DarkOrange" },
    showarrow: false,
    xanchor: "left",
    hovertext: currentPrice,
  };
  // Base order Shape
  const baseOrderS = {
    type: "line",
    xref: "x",
    yref: "y",
    x0: data.trace[0].x[0],
    y0: currentPrice,
    x1: currentTime,
    y1: currentPrice,
    line: {
      color: "DarkOrange",
      width: 2,
    },
  };
  shapes.push(baseOrderS);
  annotations.push(baseOrderA);

  if (
    !checkValue(bot.short_stop_price) &&
    parseFloat(bot.short_stop_price > 0)
  ) {
    

    // Stop loss
    const stopLossPrice = currentPrice - currentPrice * (bot.stop_loss / 100);
    // Annotation
    const stopLossA = {
      x: currentTime,
      y: stopLossPrice,
      xref: "x",
      yref: "y",
      text: "Stop loss",
      font: { color: "Blue" },
      showarrow: false,
      xanchor: "left",
    };
    // Shape
    const stopLossS = {
      type: "line",
      xref: "x",
      yref: "y",
      x0: data.trace[0].x[0],
      y0: stopLossPrice,
      x1: currentTime,
      y1: stopLossPrice,
      line: {
        color: "Blue",
        width: 4,
      },
    };
    shapes.push(stopLossS);
    annotations.push(stopLossA);
  }

  let takeProfitPrice = 0;
  let traillingStopPrice = 0
  if (bot.trailling === "true") {
    if (!checkValue(deal) && !checkValue(deal.buy_price)) {
      takeProfitPrice = parseFloat(deal.trailling_profit).toFixed(8);
      traillingStopPrice = parseFloat(deal.trailling_stop_loss_price).toFixed(8);
    } else {
      takeProfitPrice = (
        parseFloat(currentPrice) +
        parseFloat(currentPrice) * (bot.take_profit / 100)
      ).toFixed(8);
      traillingStopPrice = (
        parseFloat(currentPrice) -
        parseFloat(currentPrice) * (parseFloat(bot.trailling_deviation) / 100)
      ).toFixed(8);
    }

    if (traillingStopPrice > 0) {
      // Trailling stop loss annotations and shapes
      const traillingStopA = {
        x: takeProfitTime,
        y: traillingStopPrice,
        xref: "x",
        yref: "y",
        text: `Trailling stop loss ${checkValue(deal.trailling_stop_loss_price) ? "(inactive)" : ""}`,
        font: { color: "green" },
        showarrow: false,
        xanchor: "left",
        hovertext: traillingStopPrice,
      };
      const traillingStopS = {
        type: "line",
        xref: "x",
        yref: "y",
        x0: takeProfitTime,
        y0: traillingStopPrice,
        x1: data.trace[0].x[150],
        y1: traillingStopPrice,
        line: {
          color: "green",
          width: 4,
        },
      };
      shapes.push(traillingStopS);
      annotations.push(traillingStopA);
    }
  } else {
    // Take profit order
    takeProfitPrice = (
      parseFloat(takeProfit) +
      parseFloat(takeProfit) * (bot.take_profit / 100)
    ).toFixed(8);
    if (bot.orders.length > 0) {
      const findTp = bot.orders.find((x) => x.deal_type === "take_profit");
      if (!checkValue(findTp)) {
        takeProfitPrice = findTp.price;   
      }
    }
  }
  const takeProfitA = {
    x: takeProfitTime,
    y: takeProfitPrice,
    xref: "x",
    yref: "y",
    text: `Take profit order${bot.trailling === "true" ? " (trailling)" : ""}`,
    font: { color: "green" },
    showarrow: false,
    xanchor: "left",
    hovertext: takeProfitPrice,
  };

  const takeProfitS = {
    type: "line",
    xref: "x",
    yref: "y",
    x0: data.trace[0].x[0],
    y0: takeProfitPrice,
    x1: takeProfitTime,
    y1: takeProfitPrice,
    line: {
      color: "green",
      width: 4,
    },
  };
  shapes.push(takeProfitS);
  annotations.push(takeProfitA);

  const maxSoCount = parseInt(bot.max_so_count);
  const soOrders = bot.safety_orders;
  if (maxSoCount > 0 && Object.keys(soOrders).length > 0) {
    let previousPrice = parseFloat(currentPrice);
    Object.keys(soOrders).forEach((element, i) => {
      const price =
        previousPrice -
        previousPrice *
          (parseFloat(soOrders[element].price_deviation_so) / 100);
      previousPrice = price;
      const safetyOrderA = {
        x: currentTime,
        y: price,
        xref: "x",
        yref: "y",
        text: `Safety order ${i + 1}`,
        font: { color: "MediumPurple" },
        showarrow: false,
        xanchor: "left",
        hovertext: price.toFixed(8),
      };
      const safetyOrderS = {
        type: "line",
        xref: "x",
        yref: "y",
        x0: currentTime,
        y0: price,
        x1: data.trace[0].x[150],
        y1: price,
        line: {
          color: "MediumPurple",
          width: 2,
          dash: "dot",
        },
      };
      annotations.push(safetyOrderA);
      shapes.push(safetyOrderS);
    });
  }

  return {
    annotations: annotations,
    shapes: shapes,
  };
};
