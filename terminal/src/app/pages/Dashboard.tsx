import {
  Box,
  Card,
  Divider,
  Grid,
  SimpleGrid,
  Text,
  Title,
} from "@mantine/core";
import { motion } from "motion/react";
import { type FC } from "react";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../features/balanceApiSlice";
import { useGetBotsQuery } from "../../features/bots/botsApiSlice";
import { useBtcCloseSeriesQuery } from "../../features/kucoinApiSlice";
import {
  useFastestMoversQuery,
  useGainersLosersAggregateQuery,
} from "../../features/marketApiSlice";
import { BotStatus, MarketType } from "../../utils/enums";
import { roundDecimals } from "../../utils/math";
import { chartRevealVariants } from "../../utils/motion";
import AggregateCvdCard from "../components/AggregateCvdCard";
import BitcoinPriceCard from "../components/BitcoinPriceCard";
import CardLoadingSpinner from "../components/CardLoadingSpinner";
import FastestMovers from "../components/FastestMovers";
import GainersLosers from "../components/GainersLosers";
import GainersLosersHistoryCard from "../components/GainersLosersHistoryCard";
import PortfolioBenchmarkChart from "../components/PortfolioBenchmark";
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
      <Box
        aria-labelledby="account-overview-heading"
        mb={48}
        component="section"
      >
        <Title
          id="account-overview-heading"
          order={2}
          mt={0}
          mb={24}
          c="dimmed"
          size="h4"
        >
          Account overview
        </Title>
        <Grid>
          <Grid.Col span={{ base: 12, lg: 3 }}>
            {loadingEstimates ? (
              <CardLoadingSpinner
                label="total balance"
                className="dashboard-balance"
              />
            ) : (
              accountData && (
                <Card mb="md" className="dashboard-balance">
                  <Box>
                    <Grid>
                      <Grid.Col
                        span={{ base: 5, md: 4 }}
                        display="flex"
                        style={{
                          justifyContent: "center",
                          alignItems: "center",
                        }}
                      >
                        <Box fz="2.25rem" component="div">
                          <i className="fa-solid fa-money-bill" />
                        </Box>
                      </Grid.Col>
                      <Grid.Col span={{ base: 7, md: 8 }}>
                        <Text c="dimmed" ta="right">
                          Total Balance
                        </Text>
                        <Title order={3} fz="1.25rem" ta="right" c="info.8">
                          {roundDecimals(netTotalBalance, 2)}{" "}
                          {accountData.fiat_currency}
                        </Title>
                      </Grid.Col>
                    </Grid>
                  </Box>
                  <Divider my="sm" />
                  <SimpleGrid cols={2}>
                    <Text c="dimmed" fz=".75rem">
                      Left to allocate:
                    </Text>
                    <Text c="dimmed" ta="right">
                      {roundDecimals(accountData.fiat_available)}{" "}
                      {accountData.fiat_currency}
                    </Text>
                  </SimpleGrid>
                </Card>
              )
            )}
            {loadingEstimates || loadingBenchmark ? (
              <CardLoadingSpinner label="profit and loss" />
            ) : (
              <Card mb="md">
                <Box>
                  <Grid>
                    <Grid.Col
                      span={{ base: 5, md: 4 }}
                      display="flex"
                      style={{
                        justifyContent: "center",
                        alignItems: "center",
                      }}
                    >
                      <Box ta="center" fz="2.25rem" component="div">
                        <i
                          className={`${portfolioPnlClass} fa-solid fa-building-columns`}
                        />
                      </Box>
                    </Grid.Col>
                    <Grid.Col span={{ base: 7, md: 8 }}>
                      <div>
                        <Text ta="right" c="dimmed">
                          <span
                            className={`live-dot ${portfolioPnlClass || "tone-muted"}`}
                            aria-label="Live balance indicator"
                            role="img"
                            title="Current real-time value compared to the last balance snapshot"
                          />
                          Profit &amp; Loss
                        </Text>
                      </div>
                      <Title
                        className={`${portfolioPnlClass} metric-value value-right`}
                        order={3}
                      >
                        {portfolioPnlPercentage !== undefined &&
                          `${roundDecimals(portfolioPnlPercentage)}%`}
                      </Title>
                      <Text />
                    </Grid.Col>
                  </Grid>
                </Box>
                <Divider my="sm" />
                <SimpleGrid cols={2}>
                  <Text>(Last balance - Current real time)</Text>
                  <Text ta="right">
                    {portfolioPnlValue !== undefined &&
                      `${roundDecimals(portfolioPnlValue)} USDC`}
                  </Text>
                </SimpleGrid>
              </Card>
            )}
            {loadingBenchmark ? (
              <CardLoadingSpinner label="Sharpe ratio" />
            ) : (
              <Card mb="md">
                <Box>
                  <Grid>
                    <Grid.Col
                      span={{ base: 5, md: 4 }}
                      display="flex"
                      style={{
                        justifyContent: "center",
                        alignItems: "center",
                      }}
                    >
                      <Box ta="center" fz="2.25rem" component="div">
                        <i
                          className={`${
                            (portfolioSharpe ?? 0) > 0
                              ? "tone-success"
                              : "tone-danger"
                          } fa-solid fa-chart-line`}
                        />
                      </Box>
                    </Grid.Col>
                    <Grid.Col span={{ base: 7, md: 8 }}>
                      <div>
                        <Text ta="right" c="dimmed">
                          Sharpe ratio
                        </Text>
                      </div>
                      <Title
                        className={`${
                          (portfolioSharpe ?? 0) > 0
                            ? "tone-success"
                            : "tone-danger"
                        } metric-value value-right`}
                        order={3}
                      >
                        {portfolioSharpe !== undefined
                          ? roundDecimals(portfolioSharpe)
                          : ""}
                      </Title>
                      <Text />
                    </Grid.Col>
                  </Grid>
                </Box>
                <Divider my="sm" />
                <SimpleGrid cols={2}>
                  <Text>(How efficient are we with risk?)</Text>
                  <Text ta="right">
                    {btcSharpe !== undefined
                      ? `${roundDecimals(btcSharpe)} BTC`
                      : ""}
                  </Text>
                </SimpleGrid>
              </Card>
            )}
            {loadingActiveBots ? (
              <CardLoadingSpinner
                label="active bots"
                className="dashboard-active-bots"
              />
            ) : (
              activeBotsCount > 0 && (
                <Card mb="md" className="dashboard-active-bots">
                  <Box>
                    <div className="stats">
                      <Grid>
                        <Grid.Col
                          span={{ base: 5, md: 4 }}
                          display="flex"
                          style={{
                            justifyContent: "center",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <Box
                              c="success.5"
                              fz="2.25rem"
                              className="fa-solid fa-laptop-code"
                              component="i"
                            />
                          </div>
                        </Grid.Col>
                        <Grid.Col span={{ base: 7, md: 8 }}>
                          <Text ta="right">Active bots</Text>
                          <Title order={3} ta="right">
                            {activeBotsCount}
                          </Title>
                        </Grid.Col>
                      </Grid>
                    </div>
                  </Box>
                  <Divider mt="sm" />
                </Card>
              )
            )}
          </Grid.Col>
          <Grid.Col span={{ base: 12, lg: 9 }} className="dashboard-benchmark">
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
          </Grid.Col>
        </Grid>
      </Box>
      <Box
        aria-labelledby="market-analysis-heading"
        mb={48}
        component="section"
      >
        <Title
          id="market-analysis-heading"
          order={2}
          mt={0}
          mb={24}
          c="dimmed"
          size="h4"
        >
          Market analysis
        </Title>
        <SimpleGrid cols={{ base: 1, lg: 2 }}>
          <Box className="dashboard-movers">
            {loadingFastestMovers ? (
              <CardLoadingSpinner label="fastest futures movers" />
            ) : (
              <FastestMovers data={fastestMovers} />
            )}
          </Box>
          <Box className="dashboard-movers">
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
          </Box>
        </SimpleGrid>
        <SimpleGrid cols={{ base: 1, lg: 2 }}>
          <Box className="dashboard-trend">
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
          </Box>
          <Box className="dashboard-trend">
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
          </Box>
        </SimpleGrid>
      </Box>
      <Box
        aria-labelledby="order-book-aggregation-heading"
        mb={48}
        component="section"
      >
        <Title
          id="order-book-aggregation-heading"
          order={2}
          mt={0}
          mb={24}
          c="dimmed"
          size="h4"
        >
          Order book aggregation
        </Title>
        <Box className="dashboard-trend">
          <AggregateCvdCard />
        </Box>
      </Box>
    </div>
  );
};
export default DashboardPage;
