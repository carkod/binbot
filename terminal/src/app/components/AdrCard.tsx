import React from "react";
import Plot from "react-plotly.js";
import { Card, Row, Col } from "react-bootstrap";
import moment from "moment";

type AdrCardProps = {
  market_breadth: number[];
  strengthIndex?: number[];
  timestamps: string[];
};

const AdrCard: React.FC<AdrCardProps> = ({
  market_breadth,
  strengthIndex,
  timestamps,
}) => {
  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i
              className={`fs-2 fa fa-suitcase ${market_breadth[market_breadth.length - 1] > 0 ? "text-success" : "text-danger"}`}
            />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title as="h5" className="mt-0">
              Market Breadth Trend
            </Card.Title>
            <p className="u-text-left">
              Shows the Advancers-Decliners ratio (market breadth).
              <br />
              Over 0 indicates positive reversal Under 0 indicates negative
              reversal.
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        <Plot
          data={[
            {
              x: timestamps,
              y: market_breadth,
              type: "scatter",
              mode: "lines+markers",
              name: "Market Breadth",
              line: { color: "#007bff", width: 2 },
              marker: { size: 6 },
              fill: "tozeroy",
              fillcolor: market_breadth[market_breadth.length - 1] > 0 ? "#28a74533" : "#dc354533",
            },
            ...(strengthIndex && strengthIndex.length > 0
              ? [
                  {
                    x: timestamps,
                    y: strengthIndex,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Strength Index",
                    line: { color: "#ff9900", width: 2, dash: "dot" },
                    marker: { size: 6 },
                    fill: "none",
                  },
                ]
              : []),
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { t: 30, l: 40, r: 20, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "Market Breadth",
              showgrid: true,
              zeroline: false,
            },
            legend: { orientation: "h", y: -0.2 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      </Card.Body>
      <Card.Footer className="text-muted">
        <hr />

        {timestamps && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {moment(timestamps[0]).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default AdrCard;
