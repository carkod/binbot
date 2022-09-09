import React, { memo } from "react";
import { useImmer } from "use-immer";
import { TVChartContainer } from "binbot-charts";
import { createNewOrderLines } from "./charting.service";
import { useEffect } from "react";

export const Charting = memo(({ bot }) => {
  const [timeMarks] = useImmer([]);
  const [orderLines, setOrderLines] = useImmer([]);

  useEffect(() => {
    if (bot.deal.buy_price) {
      console.log(bot.deal)
    }
  })

  const handleTick = (ohlc) => {
    const newOrderLines = createNewOrderLines(bot, ohlc.close);
    setOrderLines(newOrderLines);
  };

  const getLatestPrice = (bar) => {
    const newOrderLines = createNewOrderLines(bot, bar[3]);
    setOrderLines(newOrderLines);
  };



  return (
    <TVChartContainer
      symbol={bot.pair}
      interval={bot.interval}
      timescaleMarks={timeMarks}
      orderLines={orderLines}
      onTick={handleTick}
      getLatestBar={getLatestPrice}
    />
  );
});

export default Charting;
