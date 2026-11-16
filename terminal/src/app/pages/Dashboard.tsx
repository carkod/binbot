import { type FC } from "react";
import { motion } from "motion/react";
import { Card, Col, Row } from "react-bootstrap";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../features/balanceApiSlice";
import { useGetBotsQuery } from "../../features/bots/botsApiSlice";
import {
  useFastestMoversQuery,
  useGainersLosersAggregateQuery,
} from "../../features/marketApiSlice";
import { useBtcCloseSeriesQuery } from "../../features/kucoinApiSlice";
import { BotStatus, MarketType } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { chartRevealVariants } from "../../utils/motion";
import GainersLosers from "../components/GainersLosers";
import FastestMovers from "../components/FastestMovers";
import PortfolioBenchmarkChart from "../components/PortfolioBenchmark";
import GainersLosersHistoryCard from "../components/GainersLosersHistoryCard";
import AggregateCvdCard from "../components/AggregateCvdCard";
import BitcoinPriceCard from "../components/BitcoinPriceCard";
import CardLoadingSpinner from "../components/CardLoadingSpinner";
import { useFilteredFuturesRankings } from "../hooks/useFilteredFuturesRankings";
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

  const { data: fastestMovers, isLoading: loadingFastestMovers } =
    useFastestMoversQuery(undefined, { pollingInterval: 5 * 60 * 1000 });

  const {
    combined: combinedFuturesRankings,
    isLoading: loadingFuturesRankings,
  } = useFilteredFuturesRankings();

  const { data: gainersLosersHistory, isLoading: loadingGainersLosersHistory } =
    useGainersLosersAggregateQuery(undefined, {
      pollingInterval: 15 * 60 * 1000,
    });
  const { data: btcCloseSeries, isLoading: loadingBtcCloseSeries } =
    useBtcCloseSeriesQuery();

  const activeBotsCount = activeBotEntities?.bots.ids.length ?? 0;
  const { portfolioPnlValue, portfolioPnlPercentage, portfolioPnlClass } =
    usePortfolioPnlDetails(benchmark, accountData);
  const portfolioSharpe = benchmark?.portfolioStats?.sharpe;
  const netTotalBalance = accountData?.estimated_total_fiat ?? 0;
  const btcSharpe = benchmark?.portfolioStats?.btc_sharpe;

  return (
    <div className="content dashboard">
      <section aria-labelledby="account-overview-heading" className="mb-5">
        <h2
          id="account-overview-heading"
          className="h4 mt-0 mb-4 text-body-secondary"
        >
          Account overview
        </h2>
        <Row>
          <Col lg="3" xs="12">
            {loadingEstimates ? (
              <CardLoadingSpinner
                label="total balance"
                className="dashboard-balance"
              />
            ) : (
              accountData && (
                <Card className="dashboard-balance">
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
              <CardLoadingSpinner
                label="active bots"
                className="dashboard-active-bots"
              />
            ) : (
              activeBotsCount > 0 && (
                <Card className="dashboard-active-bots">
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
          <Col lg="9" xs="12" sm="12" className="dashboard-benchmark">
            {loadingBenchmark ? (
              <CardLoadingSpinner label="portfolio benchmark" />
            ) : (
              benchmark?.percentageSeries.datesSeries && (
                <motion.div
                  initial="hidden"
                  animate="visible"
                  variants={chartRevealVariants}
                >
                  <PortfolioBenchmarkChart
                    chartData={benchmark.percentageSeries}
                  />
                </motion.div>
              )
            )}
          </Col>
        </Row>
      </section>
      <section aria-labelledby="market-analysis-heading" className="mb-5">
        <h2
          id="market-analysis-heading"
          className="h4 mt-0 mb-4 text-body-secondary"
        >
          Market analysis
        </h2>
        <Row>
          <Col lg="6" md="12" className="dashboard-movers">
            {loadingFastestMovers ? (
              <CardLoadingSpinner label="fastest futures movers" />
            ) : (
              <FastestMovers data={fastestMovers} />
            )}
          </Col>
          <Col lg="6" md="12" className="dashboard-movers">
            {loadingFuturesRankings ? (
              <CardLoadingSpinner label="futures gainers and losers" />
            ) : (
              combinedFuturesRankings?.length > 0 && (
                <motion.div
                  initial="hidden"
                  animate="visible"
                  variants={chartRevealVariants}
                >
                  <GainersLosers
                    data={combinedFuturesRankings}
                    market_type={MarketType.FUTURES}
                  />
                </motion.div>
              )
            )}
          </Col>
        </Row>
        <Row>
          <Col lg="6" md="12" className="dashboard-trend">
            {loadingGainersLosersHistory ? (
              <CardLoadingSpinner label="gainers versus losers trend" />
            ) : (
              gainersLosersHistory && (
                <motion.div
                  initial="hidden"
                  animate="visible"
                  variants={chartRevealVariants}
                >
                  <GainersLosersHistoryCard points={gainersLosersHistory} />
                </motion.div>
              )
            )}
          </Col>
          <Col lg="6" md="12" className="dashboard-trend">
            {loadingBtcCloseSeries ? (
              <CardLoadingSpinner label="Bitcoin price trend" />
            ) : (
              btcCloseSeries && (
                <motion.div
                  initial="hidden"
                  animate="visible"
                  variants={chartRevealVariants}
                >
                  <BitcoinPriceCard btcCloseSeries={btcCloseSeries} />
                </motion.div>
              )
            )}
          </Col>
        </Row>
      </section>
      <section
        aria-labelledby="order-book-aggregation-heading"
        className="mb-5"
      >
        <h2
          id="order-book-aggregation-heading"
          className="h4 mt-0 mb-4 text-body-secondary"
        >
          Order book aggregation
        </h2>
        <Row>
          <Col xs="12" className="dashboard-trend">
            <AggregateCvdCard />
          </Col>
        </Row>
      </section>
    </div>
  );
};

export default DashboardPage;
