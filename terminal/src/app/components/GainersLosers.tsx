import { Card, SimpleGrid } from "@mantine/core";
import type { CSSProperties } from "react";
import { computeWinnerLoserProportions } from "../../utils/dashboard-computations";
import { type MarketType } from "../../utils/enums";
import { type DashboardTicker } from "../../utils/gainers-losers";
import { roundDecimals, toPercentage } from "../../utils/math";
import GainersLosersCard from "./GainersLosersCard";

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
      <Card mb="md">
        <div className="p-line-chart">
          <div className="p-line-chart__box">
            <div
              style={{ "--market-share": perGainers } as CSSProperties}
              className="p-line-chart--left"
            >
              <span>{roundDecimals(gainerAccumulator)}</span>
            </div>
            <div
              style={{ "--market-share": perLosers } as CSSProperties}
              className="p-line-chart--right"
            >
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

        <SimpleGrid cols={2} spacing="lg">
          <GainersLosersCard
            data={gainersData}
            market_type={market_type}
            title="Today's gainers"
          />
          <GainersLosersCard
            data={losersData}
            market_type={market_type}
            title="Today's losers"
          />
        </SimpleGrid>
      </Card>
    </div>
  );
}
