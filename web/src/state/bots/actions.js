import { checkValue } from "../../validations";
import { FILTER_BY_MONTH, FILTER_BY_WEEK } from "../constants";


export function setFilterByWeek() {
  return {
    type: FILTER_BY_WEEK,
  }
}

export function setFilterByMonthState() {
  return {
    type: FILTER_BY_MONTH,
  }
}

export function getProfit(base_price, current_price) {
  if (!checkValue(base_price) && !checkValue(current_price)) {
    const percent =
      ((parseFloat(current_price) - parseFloat(base_price)) /
        parseFloat(base_price)) *
      100;
    return percent.toFixed(2);
  }
  return 0;
}

export function computeTotalProfit(bots) {
  const totalProfit = bots
    .map((bot) => bot.deal)
    .reduce((accumulator, currBot) => {
      let currTotalProfit = getProfit(currBot.buy_price, currBot.current_price);
      return parseFloat(accumulator) + parseFloat(currTotalProfit);
    }, 0);
  return totalProfit.toFixed(2);
}

export function filterByWeek(bots) {
  const today = new Date();
  const lastWeek = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate() - 7
  );
  let filteredBots = bots;
  if (bots.length > 0) {
    filteredBots = bots.filter((x) => {
      if (x.created_at) {
        return x.created_at >= lastWeek.getTime();
      }
      return true;
    });
  }
  return filteredBots;
}

export function filterByMonth(bots) {
  let today = new Date();
  today.setMonth(today.getMonth() - 1);
  today.setHours(0, 0, 0, 0);
  const lastMonth = today;

  let filteredBots = bots;
  if (bots.length > 0) {
    filteredBots = bots.filter((x) => {
      if (x.created_at) {
        return x.created_at >= lastMonth.getTime();
      }
      return true;
    });
  }
  return filteredBots;
}
