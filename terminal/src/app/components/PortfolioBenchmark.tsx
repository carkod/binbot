import { Box, Card, Grid, Group, Text, Title } from "@mantine/core";
import {
  CategoryScale,
  Chart as ChartJS,
  Title as ChartTitle,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip as Tip,
} from "chart.js";
import { type FC } from "react";
import { type BenchmarkSeriesData } from "../../features/features.types";
import { formatTimestamp } from "../../utils/time";
import { listCssColors } from "../../utils/validations";
import { useBreakpoint } from "../hooks";
import PlotlyChart from "./PlotlyChart";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ChartTitle,
  Tip,
  Legend,
);

const PortfolioBenchmarkChart: FC<{
  chartData: BenchmarkSeriesData;
}> = ({ chartData }) => {
  const breakpoint = useBreakpoint();

  let processData = { ...chartData };
  if (breakpoint === "xs") {
    // Show only the last 5 data points due to size of the screen
    processData.datesSeries = chartData.datesSeries?.slice(-5);
    processData.fiatSeries = chartData.fiatSeries?.slice(-5);
    processData.btcSeries = chartData.btcSeries?.slice(-5);
  }

  const lastUsdt = processData.fiatSeries?.[processData.fiatSeries.length - 1];

  const lastBtc = processData.btcSeries?.[processData.btcSeries.length - 1];

  // Prepare Plotly data and layout for line plot
  const plotlyData = [
    {
      x: processData.datesSeries,
      y: processData.fiatSeries,
      type: "scatter",
      mode: "lines+markers",
      name: "Portfolio value",
      line: { color: listCssColors[0], shape: "spline" },
    },
    {
      x: processData.datesSeries,
      y: processData.btcSeries,
      type: "scatter",
      mode: "lines+markers",
      name: "BTC prices",
      line: { color: listCssColors[1], shape: "spline" },
    },
  ];

  const PBLayout = {
    title: false,
    autosize: true,
    margin: { t: 10, l: 40, r: 20, b: 40 },
    legend: { orientation: "h", x: 0, y: 1.1 },
    xaxis: {
      title: "Date",
      showgrid: true,
      type: "date",
      tickformat: "%Y-%m-%d", // Show as YYYY-MM-DD
      visible: true,
    },
    yaxis: {
      title: "% Difference",
      showgrid: true,
      zeroline: true,
      gridcolor: "#eee",
    },
    responsive: true,
  };

  return (
    <Card mb="md">
      <Box mb="sm">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 1 }}>
            <i
              className={`metric-icon fa fa-suitcase ${lastUsdt > lastBtc ? "tone-success" : lastUsdt < lastBtc ? "tone-danger" : ""}`}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 11 }}>
            <Title order={5} mt={0}>
              Portfolio benchmarking
            </Title>
            <div>
              <Text>
                Compare portfolio against BTC.
                <br />
                Values in % difference
              </Text>
            </div>
          </Grid.Col>
        </Grid>
      </Box>
      <Box px={0}>
        <PlotlyChart
          data={plotlyData}
          layout={PBLayout}
          style={{ width: "100%" }}
          config={{ responsive: true }}
          useResizeHandler
        />
      </Box>
      <Group mt="sm">
        {chartData.datesSeries && (
          <div>
            <i className="fa fa-check" /> Last updated{" "}
            {formatTimestamp(
              chartData.datesSeries[chartData.datesSeries.length - 1],
            )}
          </div>
        )}
      </Group>
    </Card>
  );
};

export default PortfolioBenchmarkChart;
