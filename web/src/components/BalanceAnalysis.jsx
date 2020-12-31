import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Col, Row } from "reactstrap";

export default function BalanceAnalysis({ balances , balance_usage, balance_available, balance_available_asset }) {

    return (
        <Card>
            <CardHeader>
                <CardTitle tag="h5">Balance Analysis</CardTitle>
            </CardHeader>
            <CardBody>
                <Row className="u-margin-bottom">
                    <Col md="8" sm="12">
                        Balance usage ({100 * balance_usage}%)
                    </Col>
                    <Col md="4" sm="12">
                        {balances && balances.map((e, i) =>
                            <div key={i} className="u-primary-color"><strong>{`${e.free} ${e.asset}`}</strong></div>
                        )}
                    </Col>
                </Row>
                <Row>
                    <Col md="8" sm="12">
                        Balance available for Safety Orders
                    </Col>
                    <Col md="4" sm="12">
                        <div className="u-primary-color"><strong>{`${balance_available} ${balance_available_asset}`}</strong></div>
                    </Col>
                </Row>
                <Row>
                    <Col md="8" sm="12">
                        Total Base Order
                    </Col>
                    <Col md="4" sm="12">
                        <div className="u-primary-color"><strong>{`${balance_available} ${balance_available_asset}`}</strong></div>
                    </Col>
                </Row>
            </CardBody>
        </Card>

    );
}
