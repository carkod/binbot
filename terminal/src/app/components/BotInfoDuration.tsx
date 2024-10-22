import { ListGroupItem } from "react-bootstrap";
import { RenderTimestamp } from "./RenderTs";

const BotInfoDuration = (bot) => {
  if (bot.deal) {
    return (
      <ListGroupItem className="d-flex justify-content-between align-items-start">
        <strong>duration</strong>
        {RenderTimestamp(bot)}
      </ListGroupItem>
    );
  } else {
    return <></>;
  }
};

export default BotInfoDuration;
