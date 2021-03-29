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
  let currentPrice, currentTime, takeProfitPrice, takeProfitTime;

  // Match real base order price and time if active
  currentPrice = data.trace[0].close[data.trace[0].close.length - 1];
  currentTime = data.trace[0].x[data.trace[0].x.length - 1];

  // Match last order (last safety order triggered)
  takeProfitPrice = data.trace[0].close[data.trace[0].close.length - 1];
  takeProfitTime = data.trace[0].x[data.trace[0].x.length - 1];

  if (bot.deals.length > 0) {
    const baseOrder = bot.deals.find(x => x.deal_type === "base_order");
    if (!checkValue(baseOrder)) {
      currentPrice = baseOrder.price;
    }
  }

  // Base order
  const baseOrderA = {
    x: currentTime,
    y: currentPrice,
    xref: "x",
    yref: "y",
    text: "Base order",
    font: { color: "DarkOrange" },
    showarrow: false,
    xanchor: "left",
  };
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
      width: 4,
    },
  };
  shapes.push(baseOrderS);
  annotations.push(baseOrderA);

  // Take profit order
  const price = (
    parseFloat(takeProfitPrice) +
    parseFloat(takeProfitPrice) * (bot.take_profit / 100)
  ).toFixed(8);
  const takeProfitA = {
    x: takeProfitTime,
    y: price,
    xref: "x",
    yref: "y",
    text: "Take profit order",
    font: { color: "green" },
    showarrow: false,
    xanchor: "left",
  };

  const takeProfitS = {
    type: "line",
    xref: "x",
    yref: "y",
    x0: data.trace[0].x[0],
    y0: price,
    x1: takeProfitTime,
    y1: price,
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
      parseFloat(price) +
      parseFloat(price) * (bot.take_profit / 100)
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
  if (maxSoCount > 0) {
    let i = 0;
    let previousPrice = currentPrice;
    while (i <= maxSoCount - 1) {
      const price = (
        previousPrice -
        (previousPrice * (bot.price_deviation_so / 100))
      );
      previousPrice = price;
      const safetyOrderA = {
        x: currentTime,
        y: price,
        xref: "x",
        yref: "y",
        text: `Safety order ${i}`,
        font: { color: "blue" },
        showarrow: false,
        xanchor: "left",
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
          color: "blue",
          width: 4,
        },
      };
      annotations.push(safetyOrderA);
      shapes.push(safetyOrderS);
      i++;
    }
  }
  return {
    annotations: annotations,
    shapes: shapes,
  };
};
