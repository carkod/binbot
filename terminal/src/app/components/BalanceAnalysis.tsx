import { Card, Col, Row } from "react-bootstrap"
import { type FC } from "react"
import { type BalanceEstimateData } from "../../features/balanceApiSlice"


const accountDataAnalysis: FC<{
  accountData: BalanceEstimateData
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
                accountData?.total_fiat > 0
                  ? accountData.total_fiat.toFixed(2)
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
            {accountData.balances.map((e, i) => (
              <div key={i} className="u-primary-color">
                <strong>{`${e.free} ${e.asset}`}</strong>
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
                accountData.fiat_left > 0
                  ? accountData.fiat_left.toFixed(8)
                  : 0
              } USDC`}</strong>
            </div>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  )
}

export default accountDataAnalysis
