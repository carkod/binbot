import React from "react";
import { Card, CardBody, CardHeader, CardTitle } from "reactstrap";

export default function LogInfo({ events }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Event logs</CardTitle>
      </CardHeader>
      <CardBody>
        {events.map((item, i) => (
          <div key={i}>
            <p>{item}</p>
            <hr />
          </div>
				))}
      </CardBody>
    </Card>
  );
}
