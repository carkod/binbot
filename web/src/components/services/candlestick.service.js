import { checkValue } from "../../validations";

/**
 * Generate annotations and shapes with real base_order_price
 * @param {*} data
 * @param {*} bot
 * @returns annotations, shapes
 */
export const generateOrders = (data, bot) => {
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
  if (!checkValue(bot.deal)) {
    if ("current_price" in bot.deal) {
      const currentPriceSA = {
        x: currentTime,
        y: bot.deal.current_price,
        xref: "x",
        yref: "y",
        text: `CP`,
        font: { color: "blue" },
        showarrow: false,
        xanchor: "left",
        hovertext: bot.deal.current_price,
      };
      const currentPriceS = {
        type: "line",
        xref: "x",
        yref: "y",
        x0: currentTime,
        y0: bot.deal.current_price,
        x1: data.trace[0].x[195],
        y1: bot.deal.current_price,
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

  // Short (switch) order
  const shortOrderPrice =
    currentPrice - currentPrice * (bot.short_stop_price / 100);
  if (
    !checkValue(bot.short_stop_price) &&
    parseFloat(bot.short_stop_price > 0)
  ) {
    // Annotation
    const shortOrderA = {
      x: currentTime,
      y: shortOrderPrice,
      xref: "x",
      yref: "y",
      text: "Short Order",
      font: { color: "#FD9F23" },
      showarrow: false,
      xanchor: "left",
    };
    // Shape
    const shortOrderS = {
      type: "line",
      xref: "x",
      yref: "y",
      x0: data.trace[0].x[0],
      y0: shortOrderPrice,
      x1: currentTime,
      y1: shortOrderPrice,
      line: {
        color: "#FD9F23",
        width: 4,
      },
    };
    shapes.push(shortOrderS);
    annotations.push(shortOrderA);

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

  // Take profit order
  const takeProfitPrice = bot.orders.find((x) => x.deal_type === "take_profit");
  const takeProfitA = {
    x: takeProfitTime,
    y: takeProfitPrice,
    xref: "x",
    yref: "y",
    text: "Take profit order",
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

  if (bot.trailling === "true") {
    // Take profit trailling order
    // Should replace the take profit order, that's why uses takeProfitTime
    const traillingPrice = (
      parseFloat(takeProfitPrice) +
      parseFloat(takeProfitPrice) * (parseFloat(bot.trailling_deviation) / 100)
    ).toFixed(process.env.REACT_APP_DECIMALS);
    const traillingA = {
      x: takeProfitTime,
      y: traillingPrice,
      xref: "x",
      yref: "y",
      text: "Trailling order",
      font: { color: "green" },
      showarrow: false,
      xanchor: "left",
      hovertext: traillingPrice,
    };
    const traillingS = {
      type: "line",
      xref: "x",
      yref: "y",
      x0: takeProfitTime,
      y0: traillingPrice,
      x1: data.trace[0].x[150],
      y1: traillingPrice,
      line: {
        color: "green",
        width: 4,
      },
    };
    shapes.push(traillingS);
    annotations.push(traillingA);
  }

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
