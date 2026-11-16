import { Badge, Box, Card, Grid, Group, Text, Title } from "@mantine/core";
import moment from "moment";
import { type FC } from "react";
import type { BtcCloseSeries } from "../../features/kucoinApiSlice";
import PlotlyChart from "./PlotlyChart";

type BitcoinPriceCardProps = {
  btcCloseSeries: BtcCloseSeries;
};

const BitcoinPriceCard: FC<BitcoinPriceCardProps> = ({ btcCloseSeries }) => {
  const latestClose = btcCloseSeries.close.at(-1);

  return (
    <Card mb="md">
      <Box mb="sm">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 1 }}>
            <Box
              fz="1.875rem"
              c="warning.5"
              className="fa-brands fa-bitcoin"
              component="i"
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 11 }}>
            <Title
              order={5}
              mt={0}
              display="flex"
              style={{
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>BTC Price Trend</span>
              {latestClose !== undefined && (
                <Badge color="secondary" variant="light">
                  {latestClose.toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                  })}
                </Badge>
              )}
            </Title>
            <Text>
              {btcCloseSeries.symbol} 15-minute candlestick close price.
            </Text>
          </Grid.Col>
        </Grid>
      </Box>
      <Box>
        <PlotlyChart
          data={[
            {
              x: btcCloseSeries.timestamp,
              y: btcCloseSeries.close,
              type: "scatter",
              mode: "lines+markers",
              name: "BTC close",
              line: { color: "#f7931a", width: 2 },
              marker: { size: 5 },
              hovertemplate:
                "%{x|%d/%m %H:%M}<br>Close: %{y:,.2f}<extra>BTC</extra>",
            },
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { t: 30, l: 85, r: 20, b: 60 },
            xaxis: {
              title: { text: "Time", standoff: 14 },
              automargin: true,
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: { text: "Close price", standoff: 14 },
              automargin: true,
              showgrid: true,
              tickformat: ",.2f",
            },
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      </Box>
      <Group mt="sm" c="dimmed">
        <hr />
        {btcCloseSeries.timestamp.length > 0 && (
          <div>
            <i className="fa fa-check" /> Last updated{" "}
            {moment(btcCloseSeries.timestamp.at(-1)).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Group>
    </Card>
  );
};

export default BitcoinPriceCard;
