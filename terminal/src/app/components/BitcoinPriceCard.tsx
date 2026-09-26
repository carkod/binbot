import moment from "moment";
import { type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import type { BtcCloseSeries } from "../../features/kucoinApiSlice";
import PlotlyChart from "./PlotlyChart";

type BitcoinPriceCardProps = {
  btcCloseSeries: BtcCloseSeries;
  marketBreadthTimestamps: string[];
};

const FIFTEEN_MINUTES_MS = 15 * 60 * 1000;

const timestampBucket = (timestamp: string) =>
  Math.floor(new Date(timestamp).getTime() / FIFTEEN_MINUTES_MS);

const BitcoinPriceCard: FC<BitcoinPriceCardProps> = ({
  btcCloseSeries,
  marketBreadthTimestamps,
}) => {
  const closeByTimestamp = new Map(
    btcCloseSeries.timestamp.map((timestamp, index) => [
      timestampBucket(timestamp),
      btcCloseSeries.close[index],
    ]),
  );
  const timestamps = [...marketBreadthTimestamps].reverse();
  const closePrices = timestamps.map(
    (timestamp) => closeByTimestamp.get(timestampBucket(timestamp)) ?? null,
  );
  const latestClose = [...closePrices]
    .reverse()
    .find((close): close is number => close !== null);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i className="fs-2 fa-brands fa-bitcoin text-warning" />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>BTC Price Trend</span>
              {latestClose !== undefined && (
                <Badge bg="secondary">
                  {latestClose.toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                  })}
                </Badge>
              )}
            </Card.Title>
            <p className="u-text-left">
              {btcCloseSeries.symbol} 15-minute candlestick close price.
              <br />
              Timestamps are aligned with the Market Breadth Trend.
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        <PlotlyChart
          data={[
            {
              x: timestamps,
              y: closePrices,
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
            margin: { t: 30, l: 65, r: 20, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "Close price",
              showgrid: true,
              tickformat: ",.2f",
            },
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      </Card.Body>
      <Card.Footer className="text-muted">
        <hr />
        <div className="card-stats">
          <i className="fa fa-check" /> Last updated{" "}
          {moment(marketBreadthTimestamps[0]).format("DD/MM/YYYY HH:mm")}
        </div>
      </Card.Footer>
    </Card>
  );
};

export default BitcoinPriceCard;
