import React from "react";
import Plot from "react-plotly.js";
import { Card, Row, Col } from "react-bootstrap";
import moment from "moment";

type AdrCardProps = {
  adr: number[];
  timestamps: string[];
};

const AdrCard: React.FC<AdrCardProps> = ({ adr, timestamps }) => {
  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i
              className={`fs-2 fa fa-suitcase ${adr[adr.length - 1] > 0 ? "text-success" : "text-danger"}`}
            />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title as="h5" className="mt-0">
              ADP Trend
            </Card.Title>
            <p className="u-text-left">
              Shows the Advancers-Decliners percentage difference (ADP).
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
              y: adr,
              type: "scatter",
              mode: "lines+markers",
              name: "ADP",
              line: { color: "#007bff", width: 2 },
              marker: { size: 6 },
              fill: "tozeroy",
              fillcolor: adr[adr.length - 1] > 0 ? "#28a74533" : "#dc354533", // green if last value positive, else red
            },
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
              title: "ADP",
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
