import React from "react";
import Plot from "react-plotly.js";
import { checkValue } from "../validations";
import { botCandlestick } from "./services/bot.service";
import PropTypes from "prop-types";


function Candlestick({ data, bot = null, deal = null }) {
  let layout = {
    dragmode: "zoom",
    autosize: true,
    line_width: 50,
    margin: {
      r: 10,
      t: 25,
      b: 35,
      l: 20,
    },
    showlegend: false,
    xaxis: {
      autorange: false,
      range: [data.trace[0].x[50], data.trace[0].x[data.trace[0].x.length - 1]],
      title: "Date",
      type: "date",
    },
    yaxis: {
      domain: [0, 1],
      tickformat: ".10f",
      type: "linear",
      maxPoints: 50,
    },
  };

  if (!checkValue(bot)) {
    const { annotations, shapes } = botCandlestick(data, bot, deal);
    layout.annotations = annotations;
    layout.shapes = shapes
  }

  return (
    <Plot
      data={data.trace}
      layout={layout}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
    />
  );
}

Candlestick.propTypes = {
  data: PropTypes.object.isRequired,
  bot: PropTypes.shape({
    pair: PropTypes.string.isRequired,
  })
};

export default Candlestick;
