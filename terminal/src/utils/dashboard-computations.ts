import { roundDecimals } from "./math";

export const calculateTotalRevenue = (assets) => {
  let revenue = 0;
  let percentage = 0;

  if (assets.usdc.length > 1) {
    const usdcAssets = [...assets.usdc];
    const balances = usdcAssets.reverse();
    const yesterday = balances[0];
    const previousYesterday = balances[1];
    const diff = yesterday - previousYesterday;
    revenue = roundDecimals(diff, 4);
    percentage = roundDecimals(diff / previousYesterday, 4) * 100;
  }
  return { revenue, percentage };
};

export const computeWinnerLoserProportions = (data) => {
  let total = {
    gainerCount: 0,
    gainerAccumulator: 0,
    loserAccumulator: 0,
    loserCount: 0,
  };
  data.reduce((c, a) => {
    if (parseFloat(a.priceChangePercent) > 0) {
      total.gainerAccumulator =
        c.gainerAccumulator + parseFloat(a.priceChangePercent);
      total.gainerCount++;
      return total;
    } else {
      total.loserAccumulator =
        c.loserAccumulator + parseFloat(a.priceChangePercent);
      total.loserCount++;
      return total;
    }
  }, total);

  return total;
};
