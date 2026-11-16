import {
  Alert,
  Anchor,
  Badge,
  Box,
  Card,
  Grid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type {
  FastestMover,
  FastestMoversSnapshot,
} from "../../features/marketApiSlice";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
function MoverList({
  title,
  movers,
}: {
  title: string;
  movers: FastestMover[];
}) {
  return (
    <Box>
      <Title order={4}>{title}</Title>
      <Stack gap={0}>
        {movers.map((mover) => (
          <Box
            key={mover.symbol}
            py="xs"
            display="flex"
            className="detail-row"
            style={{
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 8,
            }}
          >
            <Anchor
              href={`/bots/futures/new/${mover.symbol}`}
              style={{
                overflowWrap: "anywhere",
              }}
            >
              {mover.symbol}
            </Anchor>
            <Box
              display="flex"
              style={{
                flexDirection: "column",
                alignItems: "flex-end",
                gap: 4,
                flexShrink: 0,
              }}
              component="div"
            >
              <Badge
                color={mover.price_change_1h_percent > 0 ? "success" : "danger"}
                variant="light"
              >
                {roundDecimals(mover.price_change_1h_percent, 2)}% in 1h
              </Badge>
              {mover.price_change_3h_percent !== null && (
                <Badge
                  color={
                    mover.price_change_3h_percent > 0 ? "success" : "danger"
                  }
                  variant="light"
                >
                  {roundDecimals(mover.price_change_3h_percent, 2)}% in 3h
                </Badge>
              )}
            </Box>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
export default function FastestMovers({
  data,
}: {
  data: FastestMoversSnapshot | undefined;
}) {
  return (
    <Card mb="md">
      <Box mb="sm">
        Fastest futures movers
        {data?.recorded_at && (
          <Text component="span" size="xs" c="dimmed" ml={8}>
            As of {formatTimestamp(data.recorded_at)}
          </Text>
        )}
        <Alert color="warning" mt={8} mb={0} py={8}>
          When gainers dominate losers, look at Rising. When losers dominate
          gainers, look at Falling.
        </Alert>
      </Box>
      {data?.comparison_at ? (
        <Grid gap={0}>
          <Grid.Col
            span={{
              base: "auto",
            }}
          >
            <MoverList title="Rising" movers={data.gainers} />
          </Grid.Col>
          <Grid.Col
            span={{
              base: "auto",
            }}
          >
            <MoverList title="Falling" movers={data.losers} />
          </Grid.Col>
        </Grid>
      ) : (
        <Box>Waiting for futures price snapshots one hour apart.</Box>
      )}
    </Card>
  );
}
