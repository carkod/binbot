import { useMemo, type FC } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../features/balanceApiSlice";
import {
  useGetBotsQuery,
  useGetAlgoRankingQuery,
} from "../../features/bots/botsApiSlice";
import { useMarketBreadthSeriesQuery } from "../../features/marketApiSlice";
import { useBtcCloseSeriesQuery } from "../../features/kucoinApiSlice";
import { useGetSignalsQuery } from "../../features/signalsApiSlice";
import { BotStatus, MarketType } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
import GainersLosers from "../components/GainersLosers";
import PortfolioBenchmarkChart from "../components/PortfolioBenchmark";
import MarketBreadthCard from "../components/MarketBreadthCard";
import BitcoinPriceCard from "../components/BitcoinPriceCard";
import CardLoadingSpinner from "../components/CardLoadingSpinner";
import { useBinquantStrategyNames } from "../hooks/useBinquantStrategyNames";
import { useFilteredFuturesRankings } from "../hooks/useFilteredFuturesRankings";
import { useFilteredGainerLosers } from "../hooks/useFilteredGainerLosers";
import { usePortfolioPnlDetails } from "../hooks/usePortfolioPnlDetails";

export const DashboardPage: FC<{}> = () => {
  const { data: accountData, isLoading: loadingEstimates } =
    useGetBalanceQuery();
  const { data: activeBotEntities, isLoading: loadingActiveBots } =
    useGetBotsQuery({
      status: BotStatus.ACTIVE,
    });
  const { data: benchmark, isLoading: loadingBenchmark } =
    useGetBenchmarkQuery();

  const { combined: combinedGainersLosers, isLoading: loadingCombined } =
    useFilteredGainerLosers();

  const {
    combined: combinedFuturesRankings,
    isLoading: loadingFuturesRankings,
  } = useFilteredFuturesRankings();

  const { data: marketBreadthSeries, isLoading: loadingMarketBreadthSeries } =
    useMarketBreadthSeriesQuery();
  const { data: btcCloseSeries, isLoading: loadingBtcCloseSeries } =
    useBtcCloseSeriesQuery();

  const { data: algoRanking, isLoading: loadingAlgoRanking } =
    useGetAlgoRankingQuery();
  const {
    strategyNames,
    isLoading: loadingStrategyNames,
    error: strategyNamesError,
  } = useBinquantStrategyNames();
  const { data: signals, isLoading: loadingSignals } = useGetSignalsQuery({
    limit: 1000,
  });

  const activeBotsCount = activeBotEntities?.bots.ids.length ?? 0;
  const { portfolioPnlValue, portfolioPnlPercentage, portfolioPnlClass } =
    usePortfolioPnlDetails(benchmark, accountData);
  const portfolioSharpe = benchmark?.portfolioStats?.sharpe;
  const netTotalBalance = accountData?.estimated_total_fiat ?? 0;
  const btcSharpe = benchmark?.portfolioStats?.btc_sharpe;
  const filteredAlgoRanking = useMemo(
    () =>
      algoRanking?.filter(({ name }) =>
        strategyNames.has(name.toLowerCase()),
      ) ?? [],
    [algoRanking, strategyNames],
  );
  const topAlgoCounts = new Set(
    filteredAlgoRanking
      .map(({ count }) => count)
      .sort((a, b) => b - a)
      .slice(0, 3),
  );
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

  return (
    <div className="content">
      <Row>
        <Col lg="3" xs="12">
          {loadingEstimates ? (
            <CardLoadingSpinner label="total balance" />
          ) : (
            accountData && (
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
            )
          )}
          {loadingEstimates || loadingBenchmark ? (
            <CardLoadingSpinner label="profit and loss" />
          ) : (
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
          )}
          {loadingBenchmark ? (
            <CardLoadingSpinner label="Sharpe ratio" />
          ) : (
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
                      <p className="text-end text-body-secondary">
                        Sharpe ratio
                      </p>
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
          )}
          {loadingActiveBots ? (
            <CardLoadingSpinner label="active bots" />
          ) : (
            activeBotsCount > 0 && (
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
                </Card.Footer>
              </Card>
            )
          )}
        </Col>
        <Col lg="9" xs="12" sm="12">
          {loadingBenchmark ? (
            <CardLoadingSpinner label="portfolio benchmark" />
          ) : (
            benchmark?.percentageSeries.datesSeries && (
              <PortfolioBenchmarkChart chartData={benchmark.percentageSeries} />
            )
          )}
        </Col>
      </Row>
      <Row>
        <Col lg="6" md="12">
          {loadingCombined ? (
            <CardLoadingSpinner label="spot gainers and losers" />
          ) : (
            combinedGainersLosers?.length > 0 && (
              <GainersLosers data={combinedGainersLosers} />
            )
          )}
        </Col>
        <Col lg="6" md="12">
          {loadingFuturesRankings ? (
            <CardLoadingSpinner label="futures gainers and losers" />
          ) : (
            combinedFuturesRankings?.length > 0 && (
              <GainersLosers
                data={combinedFuturesRankings}
                market_type={MarketType.FUTURES}
              />
            )
          )}
        </Col>
      </Row>
      <Row>
        <Col lg="6" md="12">
          {loadingMarketBreadthSeries ? (
            <CardLoadingSpinner label="market breadth trend" />
          ) : (
            marketBreadthSeries?.market_breadth && (
              <MarketBreadthCard
                marketBreadth={marketBreadthSeries.market_breadth}
                marketBreadthMa={marketBreadthSeries.market_breadth_ma}
                strengthIndex={marketBreadthSeries.strength_index}
                timestamps={marketBreadthSeries.timestamp}
              />
            )
          )}
        </Col>
        <Col lg="6" md="12">
          {loadingBtcCloseSeries || loadingMarketBreadthSeries ? (
            <CardLoadingSpinner label="Bitcoin price trend" />
          ) : (
            btcCloseSeries &&
            marketBreadthSeries?.timestamp && (
              <BitcoinPriceCard
                btcCloseSeries={btcCloseSeries}
                marketBreadthTimestamps={marketBreadthSeries.timestamp}
              />
            )
          )}
        </Col>
      </Row>
      <Row>
        {(loadingAlgoRanking ||
          loadingStrategyNames ||
          strategyNamesError ||
          filteredAlgoRanking.length > 0) && (
          <Col lg="6" md="12">
            {loadingAlgoRanking || loadingStrategyNames ? (
              <CardLoadingSpinner label="algorithm ranking" />
            ) : (
              <Card>
                <Card.Header>
                  <Card.Title
                    as="h5"
                    className="d-flex align-items-center gap-2"
                  >
                    <i className="fa-solid fa-trophy text-warning" />
                    <span>Algorithm Ranking</span>
                  </Card.Title>
                  <Card.Text className="text-body-secondary">
                    These are the algorithms executed by Binquant through
                    autotrade
                  </Card.Text>
                </Card.Header>
                <Card.Body>
                  {strategyNamesError ? (
                    <p className="text-danger" role="alert">
                      {strategyNamesError}
                    </p>
                  ) : (
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
                        {filteredAlgoRanking.map(
                          ({ name, count, bot_profit }, index) => (
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
                                  ? ((bot_profit / count) * 100).toFixed(2) +
                                    "%"
                                  : ""}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>
        )}
        {(loadingSignals || rankedSignalAlgorithms.length > 0) && (
          <Col lg="6" md="12">
            {loadingSignals ? (
              <CardLoadingSpinner label="signal ranking" />
            ) : (
              <Card>
                <Card.Header>
                  <Card.Title
                    as="h5"
                    className="d-flex align-items-center gap-2"
                  >
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
            )}
          </Col>
        )}
      </Row>
    </div>
  );
};

export default DashboardPage;
