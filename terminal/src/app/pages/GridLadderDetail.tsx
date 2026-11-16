import { Badge, Box, Card, Grid, Text, Title } from "@mantine/core";
import TVChartContainer, { Exchange } from "binbot-charts";
import { useMemo, useState, type FC } from "react";
import { useParams } from "react-router";
import type { ResolutionString } from "../../../charting_library/charting_library";
import {
  calculateCloseAdjustmentPnl,
  calculateLevelPnlSum,
  isActiveGridLadder,
  resolveGridPosition,
} from "../../features/gridLadders/gridLadders";
import { useGetGridLadderQuery } from "../../features/gridLadders/gridLaddersApiSlice";
import { useFuturesContractQuery } from "../../features/kucoinApiSlice";
import {
  buildGridOrderLines,
  buildGridTimescaleMarks,
  calculateGridLivePnl,
  calculateGridLiveReturnPct,
  calculateGridLiveUnrealizedPnl,
  chartSymbolForLadder,
  formatLogEntry,
  prominentBadgeClass,
  returnBadgeBg,
  statusBadgeBg,
} from "../../utils/grid-ladder";
import { roundDecimals } from "../../utils/math";
const GridLadderDetail: FC = () => {
  const { id = "" } = useParams();
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const { data: ladder } = useGetGridLadderQuery(id, {
    skip: !id,
    refetchOnFocus: true,
  });
  const orderLines = useMemo(
    () => (ladder ? buildGridOrderLines(ladder) : []),
    [ladder],
  );
  const timescaleMarks = useMemo(
    () => (ladder ? buildGridTimescaleMarks(ladder) : []),
    [ladder],
  );
  const exchange =
    ladder?.exchange.toLowerCase() === Exchange.KUCOIN
      ? Exchange.KUCOIN
      : Exchange.BINANCE;
  const chartSymbol = ladder ? chartSymbolForLadder(ladder) : "";
  const { data: contract } = useFuturesContractQuery(chartSymbol, {
    skip: !ladder || exchange !== Exchange.KUCOIN,
  });
  const contractMultiplier = contract?.multiplier ?? null;
  const unrealizedPnl = useMemo(() => {
    if (!ladder) {
      return 0;
    }
    if (currentPrice === null || contractMultiplier === null) {
      return ladder.unrealized_pnl;
    }
    return calculateGridLiveUnrealizedPnl(
      ladder,
      currentPrice,
      contractMultiplier,
    );
  }, [ladder, currentPrice, contractMultiplier]);
  const totalPnl = ladder ? calculateGridLivePnl(ladder, unrealizedPnl) : 0;
  const isActive = ladder ? isActiveGridLadder(ladder.status) : false;
  const levelPnl = ladder ? calculateLevelPnlSum(ladder) : 0;
  const closeAdjustmentPnl = ladder ? calculateCloseAdjustmentPnl(ladder) : 0;
  const hasCloseAdjustment = Math.abs(closeAdjustmentPnl) >= 0.00000001;
  const position = ladder
    ? resolveGridPosition(ladder)
    : { side: "flat", contracts: 0, label: "No position" };
  const gridReturnPct = ladder
    ? calculateGridLiveReturnPct(ladder, unrealizedPnl)
    : 0;
  const updateCurrentPrice = (price: number) => {
    if (!Number.isFinite(price)) {
      return;
    }
    setCurrentPrice(roundDecimals(price, 8));
  };
  if (!ladder) {
    return <Box w="100%">Grid ladder not found.</Box>;
  }
  return (
    <div className="content">
      <Box w="100%">
        <Grid>
          <Grid.Col
            span={{
              base: 12,
              sm: 12,
              md: 12,
            }}
          >
            <Card
              style={{
                display: "flex",
                flexDirection: "column",
                minHeight: "580px",
              }}
              mb="md"
            >
              <Box mb="sm">
                <Box
                  display="flex"
                  style={{
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                  component="div"
                >
                  <Title order={3} mb={0}>
                    {ladder.symbol}{" "}
                    <Badge
                      className={prominentBadgeClass}
                      color={returnBadgeBg(gridReturnPct)}
                      variant="light"
                    >
                      {gridReturnPct}%
                    </Badge>{" "}
                    {ladder.exchange}/{ladder.market_type}
                  </Title>
                  <Badge
                    className={prominentBadgeClass}
                    color={statusBadgeBg(ladder.status)}
                    variant="light"
                  >
                    {ladder.status}
                  </Badge>
                </Box>
              </Box>
              <Box
                style={{ flex: 1, display: "flex", flexDirection: "column" }}
              >
                <TVChartContainer
                  symbol={chartSymbol}
                  interval={"1h" as ResolutionString}
                  timescaleMarks={timescaleMarks}
                  orderLines={orderLines}
                  onTick={(tick) => updateCurrentPrice(parseFloat(tick.close))}
                  getLatestBar={(bar) => updateCurrentPrice(parseFloat(bar[3]))}
                  exchange={exchange}
                  style={{ minHeight: "100%", height: "600px", width: "100%" }}
                />
              </Box>
            </Card>
          </Grid.Col>
        </Grid>

        <Grid>
          <Grid.Col
            span={{
              base: 12,
              sm: 12,
              md: 7,
            }}
          >
            <Card mb="md">
              <Box
                mb="sm"
                display="flex"
                style={{
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Title order={3} mb={0}>
                  Grid Ladder
                </Title>
              </Box>
              <Box>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Algorithm</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {ladder.algorithm_name}
                  </Grid.Col>
                </Grid>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Range</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {ladder.range_low} → {ladder.range_high}
                  </Grid.Col>
                </Grid>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Breakout</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {ladder.breakout_low} / {ladder.breakout_high}
                  </Grid.Col>
                </Grid>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Current Price</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {currentPrice ?? "-"}
                  </Grid.Col>
                </Grid>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Position</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {position.contracts > 0
                      ? position.label.toUpperCase()
                      : position.label}
                  </Grid.Col>
                </Grid>
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Unrealized PnL</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {unrealizedPnl}
                  </Grid.Col>
                </Grid>
                {!isActive && (levelPnl !== 0 || hasCloseAdjustment) && (
                  <Grid mb={8}>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 4,
                      }}
                    >
                      <strong>TP Cycled PnL</strong>
                    </Grid.Col>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 8,
                      }}
                    >
                      {levelPnl}
                    </Grid.Col>
                  </Grid>
                )}
                {!isActive && hasCloseAdjustment && (
                  <Grid mb={8}>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 4,
                      }}
                    >
                      <strong>Close Adjustment</strong>
                    </Grid.Col>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 8,
                      }}
                    >
                      {closeAdjustmentPnl}
                    </Grid.Col>
                  </Grid>
                )}
                <Grid mb={8}>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 4,
                    }}
                  >
                    <strong>Total PnL</strong>
                  </Grid.Col>
                  <Grid.Col
                    span={{
                      base: 12,
                      md: 8,
                    }}
                  >
                    {totalPnl}
                  </Grid.Col>
                </Grid>
                {ladder.orders.length > 0 && (
                  <>
                    <Title order={4} mt={24} mb={16}>
                      Orders
                    </Title>
                    <Grid gap={16} mb={16}>
                      {ladder.orders.map((order) => (
                        <Grid.Col
                          key={order.id}
                          span={{
                            base: 12,
                            lg: 6,
                          }}
                        >
                          <Card mb="md" h="100%">
                            <Box>
                              <Box
                                display="flex"
                                style={{
                                  justifyContent: "space-between",
                                }}
                                component="div"
                              >
                                <strong>{order.order_role}</strong>
                                <Badge
                                  className={prominentBadgeClass}
                                  color={statusBadgeBg(order.status)}
                                  variant="light"
                                >
                                  {order.status ?? "-"}
                                </Badge>
                              </Box>
                              <Box fz="xs" mt={8} component="div">
                                Exchange order: {order.exchange_order_id}
                              </Box>
                              <Box fz="xs" component="div">
                                Side: {order.side ?? "-"}
                              </Box>
                              <Box fz="xs" component="div">
                                Price: {order.price ?? "-"}
                              </Box>
                              <Box fz="xs" component="div">
                                Contracts: {order.contracts}
                              </Box>
                              <Box fz="xs" component="div">
                                Filled: {order.filled_qty}
                                {order.filled_price
                                  ? ` @ ${order.filled_price}`
                                  : ""}
                              </Box>
                            </Box>
                          </Card>
                        </Grid.Col>
                      ))}
                    </Grid>
                  </>
                )}
                <Grid gap={16} mt={8}>
                  {ladder.levels.map((level) => (
                    <Grid.Col
                      key={level.id}
                      span={{
                        base: 12,
                        lg: 6,
                      }}
                    >
                      <Card mb="md" h="100%">
                        <Box>
                          <Box
                            display="flex"
                            style={{
                              justifyContent: "space-between",
                            }}
                            component="div"
                          >
                            <strong>Level #{level.level_index}</strong>
                            <Badge
                              className={prominentBadgeClass}
                              color={statusBadgeBg(level.status)}
                              variant="light"
                            >
                              {level.status}
                            </Badge>
                          </Box>
                          <Box fz="xs" mt={8} component="div">
                            Price: {level.price}
                          </Box>
                          <Box fz="xs" component="div">
                            Side: {level.side}
                          </Box>
                          <Box fz="xs" component="div">
                            Contracts: {level.contracts}
                          </Box>
                          <Box fz="xs" component="div">
                            Filled Qty: {level.filled_entry_qty}
                          </Box>
                          <Box fz="xs" component="div">
                            TP: {level.take_profit_price ?? "-"}
                          </Box>
                          <Box fz="xs" component="div">
                            Realized PnL: {level.realized_pnl}
                          </Box>
                        </Box>
                      </Card>
                    </Grid.Col>
                  ))}
                </Grid>
              </Box>
            </Card>
          </Grid.Col>
          <Grid.Col
            span={{
              base: 12,
              sm: 12,
              md: 5,
            }}
          >
            <Card mb="md">
              <Box mb="sm">
                <Title order={3} mb={0}>
                  Logs
                </Title>
              </Box>
              <Box>
                {ladder.logs && ladder.logs.length > 0 ? (
                  <Box
                    fz="xs"
                    bg="gray.0"
                    p={8}
                    mb={0}
                    style={{
                      ...{
                        maxHeight: "420px",
                        overflow: "auto",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      },
                      borderRadius: "var(--mantine-radius-md)",
                    }}
                    component="pre"
                  >
                    {ladder.logs.map(formatLogEntry).join("\n\n")}
                  </Box>
                ) : (
                  <Text mb={0}>No logs recorded.</Text>
                )}
              </Box>
            </Card>
          </Grid.Col>
        </Grid>
      </Box>
    </div>
  );
};
export default GridLadderDetail;
