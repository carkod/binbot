import { Box, Button, Card, Stack, Text, Title } from "@mantine/core";
import { type FC, useState } from "react";
const LogInfo: FC<{
  events: string[];
}> = ({ events }) => {
  const [showLogs, toggleLogInfo] = useState(events.length > 0);
  return (
    <Card mb="md">
      <Box
        mb="sm"
        display="flex"
        style={{
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <Title order={5}>Event logs</Title>
        </div>
        <Button onClick={() => toggleLogInfo(!showLogs)} type="button">
          {showLogs ? "Hide" : "Show"}
        </Button>
      </Box>
      {showLogs && (
        <Box>
          {[...events].reverse().map((item, i) => (
            <Stack key={i} gap={0}>
              <Box key={i} className="detail-row">
                <Text>{item}</Text>
              </Box>
            </Stack>
          ))}
        </Box>
      )}
    </Card>
  );
};
export default LogInfo;
