import { Box, Card, Grid, Group, Text, Title } from "@mantine/core";
import moment from "moment";
import { type FC } from "react";
import { type GainerLosersData } from "../../features/marketApiSlice";
import { useBreakpoint } from "../hooks";
import BarChart from "./BarChart";
type ReversalBarChartProps = {
  chartData: GainerLosersData;
  legend: any;
};
const ReversalBarChart: FC<ReversalBarChartProps> = ({ chartData, legend }) => {
  const breakpoint = useBreakpoint();
  const data = { ...chartData };
  if (breakpoint === "xs") {
    // Show only the last 5 data points due to size of the screen
    data.gainers_count = chartData.gainers_count?.slice(-10);
    data.losers_count = chartData.losers_count?.slice(-10);
    data.dates = chartData.dates?.slice(-10);
    data.gainers_percent = chartData.gainers_percent?.slice(-10);
    data.losers_percent = chartData.losers_percent?.slice(-10);
    data.gainers = chartData.gainers?.slice(-10);
    data.losers = chartData.losers?.slice(-10);
    data.total_volume = chartData.total_volume?.slice(-10);
  }
  const gainers = data.gainers_count;
  const losers = data.losers_count;
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
            <i
              className={`metric-icon fa fa-suitcase ${
                gainers > losers
                  ? "tone-success"
                  : gainers < losers
                    ? "tone-danger"
                    : ""
              }`}
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
            <Title order={5} mt={0}>
              Gainers vs. Losers by Volume
            </Title>
            <Text>
              Market evolution of gainers vs losers by volume. This graph shows
              indications of market reversal
            </Text>
          </Grid.Col>
        </Grid>
      </Box>
      {data && (
        <Box>
          <BarChart data={data} line1name="Gainers" line2name="Losers" />
        </Box>
      )}
      <Group mt="sm">
        <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="chart-legend-label">
                  <i style={{ color: x.color }} className="fa fa-circle" />
                  {x.name}
                </span>
              );
            })}
        </div>
        <hr />
        {data.dates && (
          <div>
            <i className="fa fa-check" /> Last updated{" "}
            {moment(data.dates[0]).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Group>
    </Card>
  );
};
export default ReversalBarChart;
