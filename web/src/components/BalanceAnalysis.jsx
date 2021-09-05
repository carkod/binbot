import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Col, Row } from "reactstrap";

export default function BalanceAnalysis({
  balance,
  balance_raw
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Balance Analysis</CardTitle>
      </CardHeader>
      <CardBody>
        <Row className="u-margin-bottom">
          <Col md="8" sm="12">
            Total balance in GBP<br />
            (estimated)
          </Col>
          <Col md="4" sm="12">
            <div className="u-primary-color">
              <strong>{`${
                parseFloat(balance.estimated_total_gbp) > 0
                  ? balance.estimated_total_gbp.toFixed(2)
                  : 0
              } Pounds`}</strong>
            </div>
          </Col>
        </Row>
        <Row>
          <Col md="8" sm="12">
            Porfolio of assets<br />
            (actual)
          </Col>
          <Col md="4" sm="12">
            {
              balance_raw.map((e, i) => (
                <div key={i} className="u-primary-color">
                  <strong>{`${e.free} ${e.asset}`}</strong>
                </div>
              ))}
          </Col>
        </Row>
        <hr />
        <Row>
          <Col md="8" sm="12">
            Estimated BTC value
          </Col>
          <Col md="4" sm="12">
            <div className="u-primary-color">
              <strong>{`${
                parseFloat(balance.estimated_total_btc) > 0
                  ? balance.estimated_total_btc.toFixed(8)
                  : 0
              } Bitcoin`}</strong>
            </div>
          </Col>
        </Row>
      </CardBody>
    </Card>
  );
}
