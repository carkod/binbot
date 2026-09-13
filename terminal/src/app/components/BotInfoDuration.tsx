import { ListGroupItem } from "react-bootstrap";
import type { Bot } from "../../features/bots/botInitialState";
import { renderDuration } from "../../utils/time";

const BotInfoDuration = (bot: Bot) => {
  if (bot.deal) {
    return (
      <ListGroupItem className="d-flex justify-content-between align-items-start">
        <strong>duration</strong>
        {renderDuration(bot)}
      </ListGroupItem>
    );
  } else {
    return <></>;
  }
};

export default BotInfoDuration;
