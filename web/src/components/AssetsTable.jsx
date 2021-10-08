import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Table } from "reactstrap";
import { checkValue } from "../validations";

export function AssetsTable({ data, headers }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Assets</CardTitle>
      </CardHeader>
      <CardBody>
        <Table>
          <thead className="text-primary">
            <tr>
              {!checkValue(headers) &&
                headers.map((x, i) => <th key={i}>{x}</th>)}
            </tr>
          </thead>
          <tbody>
            {!checkValue(data) &&
              data.map((x, i) => (
                <tr
                  key={i}
                >
                  <td>{x.asset}</td>
                  <td>{x.free}</td>
                  <td>{x.locked}</td>
                </tr>
              ))}
          </tbody>
        </Table>
      </CardBody>
    </Card>
  );
}
