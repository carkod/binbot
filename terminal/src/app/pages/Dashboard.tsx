import React, { useEffect, useState, type FC } from "react";
import { Card, Col, Row } from "react-bootstrap";
import {
  useGetBenchmarkQuery,
  useGetEstimateQuery,
} from "../../features/balanceApiSlice";
import { useGainerLosersQuery } from "../../features/binanceApiSlice";
import { useGetBotsQuery } from "../../features/bots/botsApiSlice";
import { useGainerLosersSeriesQuery } from "../../features/marketApiSlice";
import { calculateTotalRevenue } from "../../utils/dashboard-computations";
import { BotStatus } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { listCssColors } from "../../utils/validations";
import GainersLosers from "../components/GainersLosers";
import PortfolioBenchmarkChart from "../components/PortfolioBenchmark";
import ReversalBarChart from "../components/ReversalBarChart";

export const DashboardPage: FC<{}> = () => {
  const { data: accountData } = useGetEstimateQuery();
  const { data: activeBotEntities } = useGetBotsQuery({
    status: BotStatus.ACTIVE,
  });
  const { data: errorBotEntities } = useGetBotsQuery({
    status: BotStatus.ACTIVE,
  });
  const { data: benchmark } = useGetBenchmarkQuery();
  const { data: gainersLosersData } = useGainerLosersQuery();
  const { data: gainersLosersSeries } = useGainerLosersSeriesQuery();

  const [activeBotsCount, setActiveBotsCount] = useState(0);
  const [errorBotsCount, setErrorBotsCount] = useState(0);
  const [revenue, setRevenue] = useState<number>(0);
  const [percentageRevenue, setPercentageRevenue] = useState<number>(0);

  useEffect(() => {
    if (activeBotEntities) {
      setActiveBotsCount(activeBotEntities.bots.ids.length);
    }
    if (errorBotEntities) {
      setErrorBotsCount(errorBotEntities.bots.ids.length);
    }

    if (benchmark) {
      if (benchmark.benchmarkData) {
        const { revenue, percentage } = calculateTotalRevenue(
          benchmark.benchmarkData,
        );
        setRevenue(revenue);
        setPercentageRevenue(percentage);
      }
    }
  }, [
    accountData,
    activeBotEntities,
    errorBotEntities,
    benchmark,
    gainersLosersData,
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
                      {roundDecimals(accountData.total_fiat, 2)}{" "}
                      {accountData.asset}
                    </Card.Title>
                  </Col>
                </Row>
              </Card.Body>
              <Card.Footer>
                <hr />
                <Row>
                  <Col>
                    <p className="text-body-secondary fs-7 lh-1">
                      Left to allocate:
                    </p>
                  </Col>
                  <Col>
                    <p className="text-body-secondary text-end">
                      {roundDecimals(accountData.fiat_left)} {accountData.asset}
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
                      className={`${
                        percentageRevenue > 0 ? "text-success" : "text-danger"
                      } fa-solid fa-building-columns`}
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
                    className={`${
                      percentageRevenue > 0 ? "text-success" : "text-danger"
                    } fs-4 text-end`}
                  >
                    {`${roundDecimals(percentageRevenue)}%`}
                  </Card.Title>
                  <p />
                </Col>
              </Row>
            </Card.Body>
            <Card.Footer>
              <hr />
              <Row>
                <Col>
                  <p>(Current - Last balance)</p>
                </Col>
                <Col>
                  <p className="text-end">{roundDecimals(revenue)} USDC</p>
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
              <Card.Footer>
                <hr />
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
          {gainersLosersData?.length > 0 && (
            <GainersLosers data={gainersLosersData} />
          )}
        </Col>
        <Col lg="6" md="12">
          {gainersLosersSeries && (
            <ReversalBarChart
              chartData={gainersLosersSeries}
              legend={[
                {
                  name: "Portfolio",
                  color: listCssColors[0],
                },
              ]}
            />
          )}
        </Col>
      </Row>
    </div>
  );
};

export default DashboardPage;
