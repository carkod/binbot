import React from "react";
import Plot from "react-plotly.js";
import { Card } from "react-bootstrap";
import moment from "moment";

// Props: expects an array of ADR data objects with at least 'timestamp', 'adr', and optionally 'adr_ma'
type AdrCardProps = {
  adr: number[];
  timestamps: string[];
};

const AdrCard: React.FC<AdrCardProps> = ({ adr, timestamps }) => {
  // const timestamps = adrData.map((d) => d.timestamp);
  // const adr_ma = adrData.map((d) => d.adr_ma ?? null);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Card.Title as="h5">ADP Trend</Card.Title>
        <p className="u-text-left">
          Shows the Advancers-Decliners percentage difference (ADP).
          A mark line at 2.0 indicates a potential market reversal threshold.
        </p>
      </Card.Header>
      <Card.Body>
        <Plot
          data={[
            {
              x: timestamps,
              y: adr,
              type: "scatter",
              mode: "lines+markers",
              name: "ADR",
              line: { color: "#007bff", width: 2 },
              marker: { size: 6 },
            }
          ]}
          layout={{
            autosize: true,
            height: 320,
            margin: { t: 30, l: 40, r: 20, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "ADR",
              showgrid: true,
              zeroline: false,
            },
            shapes: [
              {
                type: "line",
                xref: "paper",
                x0: 0,
                x1: 1,
                y0: 2.0,
                y1: 2.0,
                line: {
                  color: "#e74c3c",
                  width: 2,
                  dash: "dot",
                },
                name: "Reversal Threshold",
              },
            ],
            legend: { orientation: "h", y: -0.2 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      </Card.Body>
      <hr />
      {timestamps && (
        <div className="card-stats">
          <i className="fa fa-check" /> Last updated{" "}
          {moment(timestamps[0]).format("DD/MM/YYYY HH:mm")}
        </div>
      )}
    </Card>
  );
};

export default AdrCard;
