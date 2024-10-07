import React, { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle, Button } from "reactstrap";

export default function LogInfo({ events }) {
  const [logInfo, toggleLogInfo] = useState(true)
  return (
    <Card>
      <CardHeader className="u-space-between">
        <CardTitle tag="h5">Event logs{" "}</CardTitle>
        <Button onClick={() => toggleLogInfo(!logInfo)} className="u-float-right u-space-bottom">Hide</Button>
      </CardHeader>
      {logInfo && 
      <CardBody>
        {events.map((item, i) => (
          <div key={i}>
            <p>{item}</p>
            <hr />
          </div>
				))}
      </CardBody>
      }
    </Card>
  );
}
