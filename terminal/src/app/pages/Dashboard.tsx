import React, {
  useContext,
  useEffect,
  useMemo,
  useState,
  type FC,
} from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../features/balanceApiSlice";
import {
  useGetBotsQuery,
  useGetAlgoRankingQuery,
} from "../../features/bots/botsApiSlice";
import { useAdSeriesQuery } from "../../features/marketApiSlice";
import { useGetSignalsQuery } from "../../features/signalsApiSlice";
import type {
  BalanceData,
  BenchmarkCollection,
} from "../../features/features.types";
import { BotStatus } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
import { getNetProfit } from "../../features/bots/profits";
import GainersLosers from "../components/GainersLosers";
import PortfolioBenchmarkChart from "../components/PortfolioBenchmark";
import { SpinnerContext } from "../Layout";
import AdrCard from "../components/AdrCard";
import {
  useFilteredFuturesRankings,
  useFilteredGainerLosers,
} from "../filter-gainers-losers";

type PortfolioPnlDetails = {
  portfolioPnlValue: number | undefined;
  portfolioPnlPercentage: number | undefined;
  portfolioPnlClass: string;
};

const usePortfolioPnlDetails = (
  benchmark?: BenchmarkCollection,
  accountData?: BalanceData,
): PortfolioPnlDetails => {
  const benchmarkSeries =
    benchmark?.benchmarkData?.fiat ?? benchmark?.benchmarkData?.fiat;
  const latestPortfolioValue =
    accountData?.estimated_total_fiat !== undefined
      ? accountData.estimated_total_fiat - (accountData?.total_deposit ?? 0)
      : undefined;
  const lastBenchmarkValue = benchmarkSeries?.[benchmarkSeries.length - 1];
  const previousStoredPortfolioValue =
    benchmarkSeries && benchmarkSeries.length > 1
      ? benchmarkSeries[benchmarkSeries.length - 2]
      : lastBenchmarkValue;
  const previousPortfolioValue =
    latestPortfolioValue !== undefined &&
    lastBenchmarkValue !== undefined &&
    Math.abs(lastBenchmarkValue - latestPortfolioValue) < 0.0001
      ? previousStoredPortfolioValue
      : lastBenchmarkValue;
  const portfolioPnlValue =
    latestPortfolioValue !== undefined && previousPortfolioValue !== undefined
      ? latestPortfolioValue - previousPortfolioValue
      : undefined;
  const portfolioPnlPercentage =
    portfolioPnlValue !== undefined && latestPortfolioValue
      ? (portfolioPnlValue / latestPortfolioValue) * 100
      : undefined;
  const portfolioPnlClass =
    portfolioPnlValue === undefined
      ? ""
      : portfolioPnlValue > 0
        ? "text-success"
        : "text-danger";

  return {
    portfolioPnlValue,
    portfolioPnlPercentage,
    portfolioPnlClass,
  };
};

export const DashboardPage: FC<{}> = () => {
  const { data: accountData, isLoading: loadingEstimates } =
    useGetBalanceQuery();
  const { data: activeBotEntities, isLoading: loadingActiveBots } =
    useGetBotsQuery({
      status: BotStatus.ACTIVE,
    });
  const { data: errorBotEntities, isLoading: loadingErrorBots } =
    useGetBotsQuery({
      status: BotStatus.ACTIVE,
    });
  const { data: allBotEntities, isLoading: loadingAllBots } = useGetBotsQuery({
    status: BotStatus.ALL,
  });
  const { data: benchmark, isLoading: loadingBenchmark } =
    useGetBenchmarkQuery();

  const { combined: combinedGainersLosers, isLoading: loadingCombined } =
    useFilteredGainerLosers();

  const {
    combined: combinedFuturesRankings,
    isLoading: loadingFuturesRankings,
  } = useFilteredFuturesRankings();

  const { data: adpSeries, isLoading: loadingAdpSeries } = useAdSeriesQuery();

  const { data: algoRanking, isLoading: loadingAlgoRanking } =
    useGetAlgoRankingQuery();
  const { data: signals, isLoading: loadingSignals } = useGetSignalsQuery({
    limit: 1000,
  });

  const [activeBotsCount, setActiveBotsCount] = useState(0);
  const [errorBotsCount, setErrorBotsCount] = useState(0);

  const { spinner, setSpinner } = useContext(SpinnerContext);
  const { portfolioPnlValue, portfolioPnlPercentage, portfolioPnlClass } =
    usePortfolioPnlDetails(benchmark, accountData);
  const portfolioSharpe = benchmark?.portfolioStats?.sharpe;
  const netTotalBalance = accountData?.estimated_total_fiat ?? 0;
  const btcSharpe = benchmark?.portfolioStats?.btc_sharpe;
  const topAlgoCounts = new Set(
    algoRanking
      ?.map(({ count }) => count)
      .sort((a, b) => b - a)
      .slice(0, 3) ?? [],
  );
  const top_1_symbol_pnl_share = useMemo(() => {
    const symbolPnl = new Map<string, number>();

    Object.values(allBotEntities?.bots.entities ?? {}).forEach((bot) => {
      if (!bot?.pair) return;

      symbolPnl.set(
        bot.pair,
        (symbolPnl.get(bot.pair) ?? 0) + getNetProfit(bot),
      );
    });

    const absolutePnlBySymbol = [...symbolPnl.values()]
      .map((pnl) => Math.abs(pnl))
      .filter((pnl) => pnl > 0);
    const totalAbsolutePnl = absolutePnlBySymbol.reduce(
      (total, pnl) => total + pnl,
      0,
    );

    if (totalAbsolutePnl <= 0) return undefined;

    return (Math.max(...absolutePnlBySymbol) / totalAbsolutePnl) * 100;
  }, [allBotEntities]);
  const symbolConcentrationClass =
    top_1_symbol_pnl_share === undefined
      ? ""
      : top_1_symbol_pnl_share < 50
        ? "text-success"
        : top_1_symbol_pnl_share < 75
          ? "text-warning"
          : "text-danger";
  const rankedSignalAlgorithms = useMemo(() => {
    const algorithms = new Map<
      string,
      {
        algorithm_name: string;
        generated_at: string;
        current_regime?: string | null;
        count: number;
      }
    >();

    signals?.forEach(({ algorithm_name, generated_at, current_regime }) => {
      const algorithm = algorithms.get(algorithm_name);

      if (!algorithm) {
        algorithms.set(algorithm_name, {
          algorithm_name,
          generated_at,
          current_regime,
          count: 1,
        });
        return;
      }

      algorithm.count += 1;
      if (new Date(generated_at) > new Date(algorithm.generated_at)) {
        algorithm.generated_at = generated_at;
        algorithm.current_regime = current_regime;
      }
    });

    return [...algorithms.values()].sort((left, right) => {
      const countDifference = right.count - left.count;

      if (countDifference !== 0) return countDifference;

      return (
        new Date(right.generated_at).getTime() -
        new Date(left.generated_at).getTime()
      );
    });
  }, [signals]);

  useEffect(() => {
    if (activeBotEntities) {
      setActiveBotsCount(activeBotEntities.bots.ids.length);
      setErrorBotsCount(0);
    }

    if (
      !loadingActiveBots &&
      !loadingAllBots &&
      !loadingBenchmark &&
      !loadingEstimates &&
      !loadingErrorBots &&
      !loadingCombined &&
      !loadingFuturesRankings &&
      !loadingAdpSeries &&
      !loadingAlgoRanking &&
      !loadingSignals
    ) {
      setSpinner(false);
    } else {
      setSpinner(true);
    }
  }, [
    accountData,
    activeBotEntities,
    allBotEntities,
    errorBotEntities,
    benchmark,
    combinedGainersLosers,
    combinedFuturesRankings,
    loadingActiveBots,
    loadingAllBots,
    loadingBenchmark,
    loadingEstimates,
    loadingErrorBots,
    loadingCombined,
    loadingAdpSeries,
    loadingFuturesRankings,
    loadingAlgoRanking,
    loadingSignals,
  ]);

  return (
    <div className="content">
      <Row>
        <Col lg="3" xs="12">
          {accountData && (
            <Card>
              <Card.Body>
                <Row>
                  <Col
                    md="4"
                    xs="5"
                    className="d-flex justify-content-center align-items-center"
                  >
                    <div className="fs-1">
                      <i className="fa-solid fa-money-bill" />
                    </div>
                  </Col>
                  <Col md="8" xs="7">
                    <p className="text-body-secondary text-end">
                      Total Balance
                    </p>
                    <Card.Title as="h3" className="fs-4 text-end text-info">
                      {roundDecimals(netTotalBalance, 2)}{" "}
                      {accountData.fiat_currency}
                    </Card.Title>
                  </Col>
                </Row>
              </Card.Body>
              <Card.Footer className="pt-0">
                <hr className="mt-0" />
                <Row>
                  <Col>
                    <p className="text-body-secondary fs-7 lh-1">
                      Left to allocate:
                    </p>
                  </Col>
                  <Col>
                    <p className="text-body-secondary text-end">
                      {roundDecimals(accountData.fiat_available)}{" "}
                      {accountData.fiat_currency}
                    </p>
                  </Col>
                </Row>
              </Card.Footer>
            </Card>
          )}
          <Card>
            <Card.Body>
              <Row>
                <Col
                  md="4"
                  xs="5"
                  className="d-flex justify-content-center align-items-center"
                >
                  <div className="text-center fs-1">
                    <i
                      className={`${portfolioPnlClass} fa-solid fa-building-columns`}
                    />
                  </div>
                </Col>
                <Col md="8" xs="7">
                  <div>
                    <p className="text-end text-body-secondary">
                      <span
                        className={`u-live-dot me-2 ${
                          portfolioPnlClass || "text-body-secondary"
                        }`}
                        aria-label="Live balance indicator"
                        role="img"
                        title="Current real-time value compared to the last balance snapshot"
                      />
                      Profit &amp; Loss
                    </p>
                  </div>
                  <Card.Title
                    as="h3"
                    className={`${portfolioPnlClass} fs-4 text-end`}
                  >
                    {portfolioPnlPercentage !== undefined &&
                      `${roundDecimals(portfolioPnlPercentage)}%`}
                  </Card.Title>
                  <p />
                </Col>
              </Row>
            </Card.Body>
            <Card.Footer className="pt-0">
              <hr className="mt-0" />
              <Row>
                <Col>
                  <p>(Last balance - Current real time)</p>
                </Col>
                <Col>
                  <p className="text-end">
                    {portfolioPnlValue !== undefined &&
                      `${roundDecimals(portfolioPnlValue)} USDC`}
                  </p>
                </Col>
              </Row>
            </Card.Footer>
          </Card>
          <Card>
            <Card.Body>
              <Row>
                <Col
                  md="4"
                  xs="5"
                  className="d-flex justify-content-center align-items-center"
                >
                  <div className="text-center fs-1">
                    <i
                      className={`${
                        (portfolioSharpe ?? 0) > 0
                          ? "text-success"
                          : "text-danger"
                      } fa-solid fa-chart-line`}
                    />
                  </div>
                </Col>
                <Col md="8" xs="7">
                  <div>
                    <p className="text-end text-body-secondary">Sharpe ratio</p>
                  </div>
                  <Card.Title
                    as="h3"
                    className={`${
                      (portfolioSharpe ?? 0) > 0
                        ? "text-success"
                        : "text-danger"
                    } fs-4 text-end`}
                  >
                    {portfolioSharpe !== undefined
                      ? roundDecimals(portfolioSharpe)
                      : ""}
                  </Card.Title>
                  <p />
                </Col>
              </Row>
            </Card.Body>
            <Card.Footer className="pt-0">
              <hr className="mt-0" />
              <Row>
                <Col>
                  <p>(How efficient are we with risk?)</p>
                </Col>
                <Col>
                  <p className="text-end">
                    {btcSharpe !== undefined
                      ? `${roundDecimals(btcSharpe)} BTC`
                      : ""}
                  </p>
                </Col>
              </Row>
            </Card.Footer>
          </Card>
          <Card>
            <Card.Body>
              <Row>
                <Col
                  md="4"
                  xs="5"
                  className="d-flex justify-content-center align-items-center"
                >
                  <div className="text-center fs-1">
                    <i
                      className={`${symbolConcentrationClass || "text-body-secondary"} fa-solid fa-chart-pie`}
                    />
                  </div>
                </Col>
                <Col md="8" xs="7">
                  <div>
                    <p className="text-end text-body-secondary">
                      Symbol concentration
                    </p>
                  </div>
                  <Card.Title
                    as="h3"
                    className={`${symbolConcentrationClass} fs-4 text-end`}
                  >
                    {top_1_symbol_pnl_share !== undefined
                      ? `${roundDecimals(top_1_symbol_pnl_share, 2)}%`
                      : ""}
                  </Card.Title>
                  <p />
                </Col>
              </Row>
            </Card.Body>
            <Card.Footer className="pt-0">
              <hr className="mt-0" />
              <Row>
                <Col>
                  <p>top_1_symbol_pnl_share</p>
                </Col>
                <Col>
                  <p className="text-end">bot PnL</p>
                </Col>
              </Row>
            </Card.Footer>
          </Card>
          {activeBotsCount > 0 && (
            <Card>
              <Card.Body>
                <Row>
                  <Col md="12">
                    <div className="stats">
                      <Row>
                        <Col
                          md="4"
                          xs="5"
                          className="d-flex justify-content-center align-items-center"
                        >
                          <div>
                            <i className="fa-solid fa-laptop-code text-success fs-1" />
                          </div>
                        </Col>
                        <Col md="8" xs="7">
                          <p className="text-end">Active bots</p>
                          <Card.Title as="h3" className="text-end">
                            {activeBotsCount}
                          </Card.Title>
                        </Col>
                      </Row>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
              <Card.Footer className="pt-0">
                <hr className="mt-0" />
                {errorBotsCount > 0 && (
                  <Row>
                    <Col>
                      <p className="">Errors:</p>
                    </Col>
                    <Col>
                      <p
                        className={`${errorBotsCount > 0 && "text-danger"} text-end`}
                      >
                        {errorBotsCount}{" "}
                      </p>
                    </Col>
                  </Row>
                )}
              </Card.Footer>
            </Card>
          )}
        </Col>
        <Col lg="9" xs="12" sm="12">
          {benchmark?.percentageSeries.datesSeries && (
            <PortfolioBenchmarkChart chartData={benchmark.percentageSeries} />
          )}
        </Col>
      </Row>
      <Row>
        <Col lg="6" md="12">
          {combinedGainersLosers?.length > 0 && (
            <GainersLosers data={combinedGainersLosers} />
          )}
        </Col>
        <Col lg="6" md="12">
          {combinedFuturesRankings?.length > 0 && (
            <GainersLosers data={combinedFuturesRankings} />
          )}
        </Col>
      </Row>
      <Row>
        <Col>
          {adpSeries?.adp && (
            <AdrCard
              adr={adpSeries.adp}
              strengthIndex={adpSeries.strength_index}
              timestamps={adpSeries.timestamp}
            />
          )}
        </Col>
      </Row>
      <Row>
        {algoRanking && algoRanking.length > 0 && (
          <Col lg="6" md="12">
            <Card>
              <Card.Header>
                <Card.Title as="h5" className="d-flex align-items-center gap-2">
                  <i className="fa-solid fa-trophy text-warning" />
                  <span>Algorithm Ranking</span>
                </Card.Title>
                <Card.Text className="text-body-secondary">
                  These are the algorithms executed by Binquant through
                  autotrade
                </Card.Text>
              </Card.Header>
              <Card.Body>
                <Table hover responsive size="sm">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Name</th>
                      <th className="text-end">Count</th>
                      <th className="text-end">
                        Profit ({accountData?.fiat_currency})
                      </th>
                      <th className="text-end">Performance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {algoRanking.map(({ name, count, bot_profit }, index) => (
                      <tr
                        key={name}
                        className={
                          topAlgoCounts.has(count)
                            ? "table-secondary text-white"
                            : ""
                        }
                      >
                        <td>{index + 1}</td>
                        <td>{name}</td>
                        <td className="text-end">{count}</td>
                        <td className="text-end">
                          {roundDecimals(bot_profit, 2)}%
                        </td>
                        <td className="text-end">
                          {count > 0
                            ? ((bot_profit / count) * 100).toFixed(2) + "%"
                            : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        )}
        {rankedSignalAlgorithms.length > 0 && (
          <Col lg="6" md="12">
            <Card>
              <Card.Header>
                <Card.Title as="h5" className="d-flex align-items-center gap-2">
                  <i className="fa-solid fa-signal text-info" />
                  <span>Signal Ranking</span>
                </Card.Title>
                <Card.Text className="text-body-secondary">
                  Latest strategy signals ranked by algorithm frequency
                </Card.Text>
              </Card.Header>
              <Card.Body>
                <Table hover responsive size="sm">
                  <thead>
                    <tr>
                      <th>Algorithm</th>
                      <th>Generated</th>
                      <th>Regime</th>
                      <th className="text-end">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankedSignalAlgorithms.map(
                      ({
                        algorithm_name,
                        generated_at,
                        current_regime,
                        count,
                      }) => (
                        <tr key={algorithm_name}>
                          <td>{algorithm_name}</td>
                          <td>{formatTimestamp(generated_at)}</td>
                          <td>{current_regime || "-"}</td>
                          <td className="text-end">{count}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
};

export default DashboardPage;
