import React, { type FC, useState } from "react";
import { Button, Card, ListGroup } from "react-bootstrap";

const LogInfo: FC<{
  events: string[];
}> = ({ events }) => {
  const [showLogs, toggleLogInfo] = useState(events.length > 0);
  return (
    <Card>
      <Card.Header className="u-space-between">
        <Card.Title as="h5">Event logs </Card.Title>
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
