import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Row from "react-bootstrap/Row";
import { computeWinnerLoserProportions } from "../../utils/dashboard-computations";
import { roundDecimals } from "../../utils/math";
import GainersLosersCard from "./GainersLosersCard";

export default function GainersLosers({ data }) {
  const { gainerCount, gainerAccumulator, loserAccumulator, loserCount } =
    computeWinnerLoserProportions(data);
  // Top 10
  const gainersData = data.slice(0, 10);
  const perGainers = roundDecimals((gainerCount / data.length)) * 100 + "%";
  // Bottom 10
  const losersData = data.slice(-10).reverse();
  const perLosers = roundDecimals((loserCount / data.length)) * 100 + "%";
  return (
    <div>
      <Card border="success">
        <div className="p-line-chart">
          <div className="p-line-chart__box">
            <div className="p-line-chart--left" style={{ width: perGainers }}>
              <span>{roundDecimals(gainerAccumulator)}</span>
            </div>
            <div className="p-line-chart--right" style={{ width: perLosers }}>
              <span>{roundDecimals(loserAccumulator)}</span>
            </div>
          </div>
          <div className="p-line-chart--legend">
            <div>
              Gainers: <span>{perGainers}</span>
            </div>
            <div>
              Losers: <span>{perLosers}</span>
            </div>
          </div>
        </div>

        <Row>
          <Col>
            <GainersLosersCard
              data={gainersData}
              title="Today's gainers in USDC market"
            />
          </Col>
          <Col>
            <GainersLosersCard
              data={losersData}
              title="Today's losers in USDC market"
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
}
