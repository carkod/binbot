import React from "react";
import PieChart from "../../components/PieChart";
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  CardTitle,
  Col,
  Row,
} from "reactstrap";

export function AssetsPie({ data, legend }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Assets</CardTitle>
      </CardHeader>
      <CardBody>
        {data && <PieChart data={data} />}
      </CardBody>
      <CardFooter>
        <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="u-text-margin-left">
                  <i className="fa fa-circle" style={{ color: x.color }} />
                  {x.name}
                </span>
              );
            })}
        </div>
      </CardFooter>
    </Card>
  );
}
