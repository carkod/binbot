import { Badge, Box, Card, Grid, Group, Text, Title } from "@mantine/core";
import moment from "moment";
import type { FC } from "react";
import type { GainersLosersAggregatePoint } from "../../features/marketApiSlice";
import PlotlyChart from "./PlotlyChart";
type GainersLosersHistoryCardProps = {
  points: GainersLosersAggregatePoint[];
};
const BALANCE_COLOR = "#51cbce";
const GainersLosersHistoryCard: FC<GainersLosersHistoryCardProps> = ({
  points,
}) => {
  const history = [...points]
    .sort(
      (left, right) =>
        new Date(left.timestamp).getTime() -
        new Date(right.timestamp).getTime(),
    )
    .map((point) => {
      const gain = point.gainer_magnitude;
      const loss = point.loser_magnitude;
      const magnitude = gain + loss;
      return {
        timestamp: point.timestamp,
        gainShare: magnitude > 0 ? (gain / magnitude) * 100 : null,
        lossShare: magnitude > 0 ? (loss / magnitude) * 100 : null,
        balance: magnitude > 0 ? ((gain - loss) / magnitude) * 100 : null,
        advancers: point.advancers,
        decliners: point.decliners,
      };
    });
  const latest = history.at(-1);
  const hasHistory = history.some((point) => point.balance !== null);
  const timestamps = history.map((point) => point.timestamp);
  const hoverData = history.map((point) => [
    point.gainShare ?? 0,
    point.lossShare ?? 0,
    point.advancers,
    point.decliners,
  ]);
  return (
    <Card mb="md">
      <Box mb="sm">
        <Grid>
          <Grid.Col
            span={{
              base: 12,
              sm: 1,
              md: 1,
              lg: 1,
            }}
          >
            <Box
              fz="1.875rem"
              c="success.5"
              className="fa fa-chart-area"
              component="i"
            />
          </Grid.Col>
          <Grid.Col
            span={{
              base: 12,
              sm: 11,
              md: 11,
              lg: 11,
            }}
          >
            <Title
              order={5}
              mt={0}
              display="flex"
              style={{
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>Gainers vs Losers Trend</span>
              {latest?.balance !== null && latest?.balance !== undefined && (
                <Badge
                  color={
                    latest.balance > 0
                      ? "success"
                      : latest.balance < 0
                        ? "danger"
                        : "secondary"
                  }
                  variant="light"
                >
                  Balance {latest.balance > 0 ? "+" : ""}
                  {latest.balance.toFixed(1)}%
                </Badge>
              )}
            </Title>
            <Text mb={0}>
              Every 15 minutes, this samples the rolling 24h moves of all
              registered, active KuCoin futures contracts. The line shows gain
              magnitude minus loss magnitude as a percentage of their combined
              magnitude. Above zero, gainers lead; below zero, losers lead.
            </Text>
          </Grid.Col>
        </Grid>
      </Box>
      <Box>
        {hasHistory ? (
          <PlotlyChart
            data={[
              {
                x: timestamps,
                y: history.map((point) => point.balance),
                type: "scatter",
                mode: "lines",
                name: "Gain/loss balance",
                line: { color: BALANCE_COLOR, width: 3 },
                customdata: hoverData,
                hovertemplate:
                  "Balance %{y:+.1f}%<br>Gainers: %{customdata[0]:.1f}% share (%{customdata[2]:.0f} contracts)<br>Losers: %{customdata[1]:.1f}% share (%{customdata[3]:.0f} contracts)<extra></extra>",
              },
            ]}
            layout={{
              autosize: true,
              height: 460,
              margin: { t: 30, l: 95, r: 20, b: 125 },
              hovermode: "x unified",
              xaxis: {
                title: { text: "Time", standoff: 14 },
                automargin: true,
                tickformat: "%d/%m %H:%M",
                showgrid: false,
              },
              yaxis: {
                title: { text: "Gain/loss balance (%)", standoff: 14 },
                automargin: true,
                range: [-100, 100],
                zeroline: true,
                zerolinecolor: "#6c757d",
                showgrid: true,
              },
              legend: {
                orientation: "h",
                x: 0.5,
                xanchor: "center",
                y: -0.31,
                yanchor: "top",
              },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%", height: "100%" }}
            useResizeHandler={true}
          />
        ) : (
          <Box c="dimmed" component="div">
            Waiting for 15-minute futures price snapshots.
          </Box>
        )}
      </Box>
      <Group mt="sm" c="dimmed">
        <hr />
        {latest && (
          <div>
            <i className="fa fa-check" /> Last updated{" "}
            {moment(latest.timestamp).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Group>
    </Card>
  );
};
export default GainersLosersHistoryCard;
