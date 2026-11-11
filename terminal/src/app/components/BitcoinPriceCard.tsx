import moment from "moment";
import { type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import type { BtcCloseSeries } from "../../features/kucoinApiSlice";
import PlotlyChart from "./PlotlyChart";

type BitcoinPriceCardProps = {
  btcCloseSeries: BtcCloseSeries;
};

const BitcoinPriceCard: FC<BitcoinPriceCardProps> = ({ btcCloseSeries }) => {
  const latestClose = btcCloseSeries.close.at(-1);

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
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
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
      </Card.Body>
      <Card.Footer className="text-muted">
        <hr />
        {btcCloseSeries.timestamp.length > 0 && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {moment(btcCloseSeries.timestamp.at(-1)).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default BitcoinPriceCard;
