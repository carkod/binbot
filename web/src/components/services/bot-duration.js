import moment from "moment";

function botDuration(start, end) {
  const startTime = moment(start);
  const endTime = moment(end);
  const duration = moment.duration(endTime.diff(startTime));

  let days = Math.floor(duration.asDays());
  duration.subtract(moment.duration(days, "days"));

  let hours = duration.hours();
  duration.subtract(moment.duration(hours, "hours"));

  let minutes = duration.minutes();
  duration.subtract(moment.duration(minutes, "minutes"));

  const seconds = duration.seconds();
  let dateStringify = `${seconds}s`;

  if (minutes > 0) {
    dateStringify = `${minutes}m ${dateStringify}`;
  }
  if (hours > 0) {
    dateStringify = `${hours}h ${dateStringify}`;
  }
  if (days > 0) {
    dateStringify = `${days}d ${dateStringify}`;
  }

  return dateStringify;
}

export default function renderTimestamp(bot) {

    let enterPositionTs = new Date().getTime();
    let exitPositionTs = new Date().getTime();

    // Duration for long positions
    if (bot.deal.buy_timestamp > 0) {
        enterPositionTs = bot.deal.buy_timestamp
    }
    if (bot.deal.sell_timestamp > 0) {
        exitPositionTs = bot.deal.sell_timestamp
    }

    // Duration for short positions
    if (bot.deal.margin_short_sell_timestamp > 0) {
        enterPositionTs = bot.deal.margin_short_sell_timestamp
    }
    if (bot.deal.margin_short_buy_back_timestamp > 0) {
        exitPositionTs = bot.deal.margin_short_buy_back_timestamp
    }

    const duration = botDuration(enterPositionTs, exitPositionTs);

    return duration;
}