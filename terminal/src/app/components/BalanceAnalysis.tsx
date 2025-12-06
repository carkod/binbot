import React, { type FC } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { type BalanceData } from "../../features/balanceApiSlice";

const BalanceAnalysis: FC<{
  accountData: BalanceData;
}> = ({ accountData }) => {
  return (
    <Card>
      <Card.Header>
        <Card.Title as="h5">Account breakdown</Card.Title>
      </Card.Header>
      <Card.Body>
        <Row className="u-margin-bottom">
          <Col md="8" sm="12">
            Total fiat value
            <br />
            (USDC)
          </Col>
          <Col md="4" sm="12">
            <div className="u-primary-color">
              <strong>{`${
                accountData?.estimated_total_fiat > 0
                  ? accountData.estimated_total_fiat.toFixed(2)
                  : 0
              } USDC`}</strong>
            </div>
          </Col>
        </Row>
        <Row>
          <Col md="8" sm="12">
            Porfolio of assets
            <br />
            (actual)
          </Col>
          <Col md="4" sm="12">
            {Object.entries(accountData.balances).map(([asset, amount], i) => (
              <div key={i} className="u-primary-color">
                <strong>{`${amount} ${asset}`}</strong>
              </div>
            ))}
          </Col>
        </Row>
        <hr />
        <Row>
          <Col md="8" sm="12">
            Free fiat left
          </Col>
          <Col md="4" sm="12">
            <div className="u-primary-color">
              <strong>{`${
                accountData.fiat_available > 0
                  ? accountData.fiat_available.toFixed(8)
                  : 0
              } USDC`}</strong>
            </div>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  );
};

export default BalanceAnalysis;
