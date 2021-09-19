import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Table } from "reactstrap";

export const ErrorLog = ({ errors }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Bot Errors</CardTitle>
      </CardHeader>
      <CardBody>
        <Table>
          <tbody>
            {errors &&
              errors.map((x, i) => (
                <tr key={i}>
                  <td>{x}</td>
                </tr>
              ))}
          </tbody>
        </Table>
      </CardBody>
    </Card>
  );
};
