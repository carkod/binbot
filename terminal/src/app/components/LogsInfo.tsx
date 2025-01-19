import React, { type FC, useState } from "react";
import { Button, Card, ListGroup } from "react-bootstrap";

const LogInfo: FC<{
  events: string[];
}> = ({ events }) => {
  const [logInfo, toggleLogInfo] = useState(true);
  return (
    <Card>
      <Card.Header className="u-space-between">
        <Card.Title as="h5">Event logs </Card.Title>
        <Button
          onClick={() => toggleLogInfo(!logInfo)}
          className="u-float-right u-space-bottom"
        >
          Hide
        </Button>
      </Card.Header>
      {logInfo && (
        <Card.Body>
          {events.map((item, i) => (
            <ListGroup className="list-group-flush">
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
