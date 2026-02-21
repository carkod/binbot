import React, { type FC } from "react";
import { Card, Col, Row, Badge } from "react-bootstrap";
import { type BalanceData } from "../../features/features.types";
import { type MarketType } from "../../utils/enums";
import { capitalizeFirst } from "../../utils/strings";

const BalanceAnalysis: FC<{
  accountData: BalanceData;
  marketType: MarketType;
}> = ({ accountData, marketType }) => {
  const marketLabel = capitalizeFirst(marketType.toLowerCase());
  return (
    <Card>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <Card.Title as="h5">Account breakdown</Card.Title>
        <Badge bg="secondary" className="text-uppercase">
          {marketLabel}
        </Badge>
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
            Portfolio of assets
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
