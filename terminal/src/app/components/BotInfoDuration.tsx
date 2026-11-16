import { Box } from "@mantine/core";
import type { Bot } from "../../features/bots/botInitialState";
import { renderDuration } from "../../utils/time";
const BotInfoDuration = (bot: Bot) => {
  if (bot.deal) {
    return (
      <Box className="detail-row">
        <strong>duration</strong>
        {renderDuration(bot)}
      </Box>
    );
  } else {
    return <></>;
  }
};
export default BotInfoDuration;
