import React, { useContext, useEffect, useState, type FC } from "react";
import { Card, Col, Row } from "react-bootstrap";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../features/balanceApiSlice";
import { useGetBotsQuery } from "../../features/bots/botsApiSlice";
import { useAdSeriesQuery } from "../../features/marketApiSlice";
import type {
  BalanceData,
  BenchmarkCollection,
} from "../../features/features.types";
import { BotStatus } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
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
  const previousPortfolioValue = benchmarkSeries?.[benchmarkSeries.length - 1];
  const latestPortfolioValue = accountData?.estimated_total_fiat;
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
  const { data: benchmark, isLoading: loadingBenchmark } =
    useGetBenchmarkQuery();

  const { combined: combinedGainersLosers, isLoading: loadingCombined } =
    useFilteredGainerLosers();

  const {
    combined: combinedFuturesRankings,
    isLoading: loadingFuturesRankings,
  } = useFilteredFuturesRankings();

  const { data: adpSeries, isLoading: loadingAdpSeries } = useAdSeriesQuery();

  const [activeBotsCount, setActiveBotsCount] = useState(0);
  const [errorBotsCount, setErrorBotsCount] = useState(0);

  const { spinner, setSpinner } = useContext(SpinnerContext);
  const { portfolioPnlValue, portfolioPnlPercentage, portfolioPnlClass } =
    usePortfolioPnlDetails(benchmark, accountData);

  useEffect(() => {
    if (activeBotEntities) {
      setActiveBotsCount(activeBotEntities.bots.ids.length);
      setErrorBotsCount(0);
    }

    if (
      !loadingActiveBots &&
      !loadingBenchmark &&
      !loadingEstimates &&
      !loadingErrorBots &&
      !loadingCombined &&
      !loadingFuturesRankings &&
      !loadingAdpSeries
    ) {
      setSpinner(false);
    } else {
      setSpinner(true);
    }
  }, [
    accountData,
    activeBotEntities,
    errorBotEntities,
    benchmark,
    combinedGainersLosers,
    combinedFuturesRankings,
    loadingActiveBots,
    loadingBenchmark,
    loadingEstimates,
    loadingErrorBots,
    loadingCombined,
    loadingAdpSeries,
    loadingFuturesRankings,
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
                      {roundDecimals(accountData?.estimated_total_fiat, 2)}{" "}
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
                        benchmark?.portfolioStats?.sharpe > 0
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
                      benchmark?.portfolioStats?.sharpe > 0
                        ? "text-success"
                        : "text-danger"
                    } fs-4 text-end`}
                  >
                    {benchmark?.portfolioStats?.sharpe
                      ? roundDecimals(benchmark.portfolioStats.sharpe)
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
                    {benchmark?.portfolioStats?.sharpe
                      ? roundDecimals(benchmark.portfolioStats.sharpe)
                      : ""}
                  </p>
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
    </div>
  );
};

export default DashboardPage;
