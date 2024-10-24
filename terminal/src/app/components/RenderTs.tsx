import moment from "moment";
import { renderDuration } from "../../utils/time";
import { Col, Row } from "react-bootstrap";
import { BotStatus, BotStrategy } from "../../utils/enums";

/**
 * Format timestamp by converting it to datetime format
 * @param {string} timestamp in milliseconds
 * @returns
 */
export const formatTimestamp = (timestamp) => {
  return timestamp === 0 ? "0" : moment(timestamp).format("D MMM, HH:mm");
};

const TimestampComponent = ({ label, timestamp }) => {
  return (
    <Row>
      <Col md="6" xs="7">
        <p className="small">{label}</p>
      </Col>
      <Col md="6" xs="5">
        <p className="small">{formatTimestamp(timestamp)}</p>
      </Col>
    </Row>
  );
};

/**
 * Render deal bot opening and closing timestamp
 * based on strategy. Timestamps short position bots
 * are flipped compared to long positions.
 *
 * @param {Bot} bot
 */
const RenderTimestamp = (bot) => {
  if (bot.strategy === BotStrategy.LONG) {
    if (bot.deal?.buy_timestamp > 0 && bot.deal?.sell_timestamp > 0) {
      return (
        <>
          <TimestampComponent
            label="Open time"
            timestamp={bot.deal?.buy_timestamp}
          />
          <TimestampComponent
            label="Close time"
            timestamp={bot.deal?.sell_timestamp}
          />
        </>
      );
    } else if (bot.deal?.buy_timestamp > 0) {
      return (
        <TimestampComponent
          label="Open time"
          timestamp={bot.deal?.buy_timestamp}
        />
      );
    }
  }

  // margin bots
  if (bot.strategy === BotStrategy.MARGIN_SHORT) {
    if (
      bot.deal?.margin_short_sell_timestamp > 0 &&
      bot.deal?.margin_short_buy_back_timestamp > 0
    ) {
      return (
        <>
          <TimestampComponent
            label="Open time"
            timestamp={bot.deal?.margin_short_sell_timestamp}
          />
          <TimestampComponent
            label="Close time"
            timestamp={bot.deal?.sell_timestamp}
          />
        </>
      );
    } else if (bot.deal?.margin_short_sell_timestamp > 0) {
      return (
        <TimestampComponent
          label="Open time"
          timestamp={bot.deal?.margin_short_sell_timestamp}
        />
      );
    }
  }
};

const DurationTsComponent = (bot) => {
  // Long positions
  if (bot.deal) {
    return <p className="small">{renderDuration(bot)}</p>;
  } else {
    return <></>;
  }
};

export { RenderTimestamp, DurationTsComponent };
