import { type FC, useState } from "react";
import { Button, Card } from "react-bootstrap";

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
            <div key={i}>
              <p>{item}</p>
              <hr />
            </div>
          ))}
        </Card.Body>
      )}
    </Card>
  );
};

export default LogInfo;
