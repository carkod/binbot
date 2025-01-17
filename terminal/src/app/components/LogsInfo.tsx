import { type FC, useState } from "react";
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
            <ListGroup variant="flush">
              <ListGroup.Item
                action
                as="h5"
                key={i}
                className="d-flex justify-content-between align-items-start"
              >
                {item}
              </ListGroup.Item>
            </ListGroup>
          ))}
        </Card.Body>
      )}
    </Card>
  );
};

export default LogInfo;
