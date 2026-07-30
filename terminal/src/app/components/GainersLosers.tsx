import Card from "react-bootstrap/Card";
import Col from "react-bootstrap/Col";
import Row from "react-bootstrap/Row";
import { computeWinnerLoserProportions } from "../../utils/dashboard-computations";
import { type DashboardTicker } from "../../utils/gainers-losers";
import { roundDecimals, toPercentage } from "../../utils/math";
import GainersLosersCard from "./GainersLosersCard";
import { type MarketType } from "../../utils/enums";

export interface GainersLosersProps {
  data: DashboardTicker[];
  market_type?: MarketType;
}

export default function GainersLosers({
  data,
  market_type,
}: GainersLosersProps) {
  const { gainerCount, gainerAccumulator, loserAccumulator, loserCount } =
    computeWinnerLoserProportions(data);
  // Top 10
  const gainersData = data.slice(0, 10);
  const perGainers = `${toPercentage(gainerCount / data.length) ?? 0}%`;
  // Bottom 10
  const losersData = data.slice(-10).reverse();
  const perLosers = `${toPercentage(loserCount / data.length) ?? 0}%`;
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
              market_type={market_type}
              title="Today's gainers"
            />
          </Col>
          <Col>
            <GainersLosersCard
              data={losersData}
              market_type={market_type}
              title="Today's losers"
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
}
