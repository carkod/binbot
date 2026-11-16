import { Box } from "@mantine/core";
import type { Bot } from "../../features/bots/botInitialState";
import { renderDuration } from "../../utils/time";
const BotInfoDuration = (bot: Bot) => {
  if (bot.deal) {
    return (
      <Box
        py="xs"
        display="flex"
        className="detail-row"
        style={{
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <strong>duration</strong>
        {renderDuration(bot)}
      </Box>
    );
  } else {
    return <></>;
  }
};
export default BotInfoDuration;
