import React from "react";
import { Card, CardBody, CardHeader, CardTitle } from "reactstrap";

export default function LogInfo({ info }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Logs</CardTitle>
      </CardHeader>
      <CardBody>
        {info.map((item) => (
          <>
            <p>{item}</p>
            <hr />
          </>
				))}
      </CardBody>
    </Card>
  );
}
