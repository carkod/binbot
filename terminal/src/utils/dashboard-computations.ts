import {
  type DashboardTicker,
  normalizePriceChangePercent,
} from "./gainers-losers";

export const computeWinnerLoserProportions = (data: DashboardTicker[] = []) => {
  let total = {
    gainerCount: 0,
    gainerAccumulator: 0,
    loserAccumulator: 0,
    loserCount: 0,
  };
  data.reduce((c, a) => {
    const aPcp = parseFloat(normalizePriceChangePercent(a));

    if (aPcp > 0) {
      total.gainerAccumulator = c.gainerAccumulator + aPcp;
      total.gainerCount++;
      return total;
    } else {
      total.loserAccumulator = c.loserAccumulator + aPcp;
      total.loserCount++;
      return total;
    }
  }, total);

  return total;
};
