import React, { type FC, useState } from "react";
import { Button, Card, ListGroup, Badge } from "react-bootstrap";
import { type MarketType } from "../../utils/enums";
import { capitalizeFirst } from "../../utils/strings";

const LogInfo: FC<{
  events: string[];
  marketType: MarketType;
}> = ({ events, marketType }) => {
  const [showLogs, toggleLogInfo] = useState(events.length > 0);
  const marketLabel = capitalizeFirst(marketType.toLowerCase());
  return (
    <Card>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <Card.Title as="h5">Event logs</Card.Title>
          <Badge bg="secondary" className="text-uppercase">
            {marketLabel}
          </Badge>
        </div>
        <Button
          onClick={() => toggleLogInfo(!showLogs)}
          className="u-float-right u-space-bottom"
        >
          {showLogs ? "Hide" : "Show"}
        </Button>
      </Card.Header>
      {showLogs && (
        <Card.Body>
          {[...events].reverse().map((item, i) => (
            <ListGroup key={i} className="list-group-flush">
              <ListGroup.Item
                action
                as="small"
                key={i}
                className="d-flex justify-content-between align-items-start"
              >
                <p>{item}</p>
              </ListGroup.Item>
            </ListGroup>
          ))}
        </Card.Body>
      )}
    </Card>
  );
};

export default LogInfo;
