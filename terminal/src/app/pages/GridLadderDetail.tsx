import { useMemo, type FC } from "react";
import { Badge, Card, Col, Container, Row } from "react-bootstrap";
import { useParams } from "react-router";
import { useGetGridLadderQuery } from "../../features/gridLadders/gridLaddersApiSlice";
import type { GridLadder, GridLevel } from "../../features/gridLadders/types";
import { MarketType } from "../../utils/enums";
import { capitalizeFirst } from "../../utils/strings";
import { dealColors } from "../../utils/charting";
import type { OrderLine } from "../../utils/charting/index.d";
import TVChartContainer, { Exchange } from "binbot-charts";
import type { ResolutionString } from "../../../charting_library/charting_library";
import { calculateGridPnl } from "../../features/gridLadders/gridLadders";
import { roundDecimals } from "../../utils/math";

const formatLogEntry = (log: unknown): string => {
  if (typeof log === "string") {
    return log;
  }

  return JSON.stringify(log, null, 2) ?? String(log);
};

const gridLevelColor = (level: GridLevel): string => {
  if (level.side === "buy") {
    return dealColors.base_order;
  }
  if (level.side === "sell") {
    return dealColors.safety_order;
  }
  return "#6c757d";
};

const gridLevelLabel = (level: GridLevel): string => {
  if (level.side === "neutral") {
    return `L${level.level_index} neutral`;
  }
  return `L${level.level_index} ${capitalizeFirst(level.side)}`;
};

const buildGridOrderLines = (ladder: GridLadder): OrderLine[] =>
  ladder.levels.flatMap((level) => {
    const quantity = `${level.contracts} contracts`;
    const lines: OrderLine[] = [
      {
        id: `${level.id}-entry`,
        text: gridLevelLabel(level),
        tooltip: [
          `Status: ${level.status}`,
          `Side: ${level.side}`,
          `Margin: ${level.margin_required} ${ladder.fiat}`,
        ],
        quantity,
        price: level.filled_entry_price || level.price,
        color: gridLevelColor(level),
        lineStyle: level.side === "neutral" ? 2 : undefined,
      },
    ];

    if (level.take_profit_price) {
      lines.push({
        id: `${level.id}-take-profit`,
        text: `L${level.level_index} TP`,
        tooltip: [
          `Status: ${level.status}`,
          `Entry: ${level.filled_entry_price || level.price}`,
          `Take profit: ${level.take_profit_price}`,
        ],
        quantity: `${level.filled_entry_qty || level.contracts} contracts`,
        price: level.take_profit_price,
        color: dealColors.take_profit,
        lineStyle: 2,
      });
    }

    return lines;
  });

const chartSymbolForLadder = (ladder: GridLadder): string => {
  const exchange = ladder.exchange.toLowerCase();
  const marketType = ladder.market_type.toUpperCase();

  if (exchange !== Exchange.KUCOIN) {
    return ladder.symbol;
  }
  if (marketType === MarketType.FUTURES) {
    return ladder.symbol.endsWith("M") ? ladder.symbol : `${ladder.symbol}M`;
  }
  if (ladder.symbol.includes("-")) {
    return ladder.symbol;
  }

  const baseAsset = ladder.symbol.replace(ladder.fiat, "");
  return `${baseAsset}-${ladder.fiat}`;
};

const isErrorStatus = (status?: string | null): boolean => {
  const value = status?.toLowerCase() ?? "";
  return ["error", "rejected", "expired", "range_broken"].some((errorStatus) =>
    value.includes(errorStatus),
  );
};

const statusBadgeBg = (status?: string | null): "success" | "danger" =>
  isErrorStatus(status) ? "danger" : "success";

const returnBadgeBg = (
  returnPct: number,
): "success" | "danger" | "secondary" => {
  if (returnPct > 0) {
    return "success";
  }
  if (returnPct < 0) {
    return "danger";
  }
  return "secondary";
};

const calculateGridReturnPct = (ladder: GridLadder): number => {
  if (ladder.total_margin <= 0) {
    return 0;
  }

  return roundDecimals((calculateGridPnl(ladder) / ladder.total_margin) * 100);
};

const prominentBadgeClass = "";

const GridLadderDetail: FC = () => {
  const { id = "" } = useParams();
  const { data: ladder } = useGetGridLadderQuery(id, {
    skip: !id,
    refetchOnFocus: true,
  });
  const orderLines = useMemo(
    () => (ladder ? buildGridOrderLines(ladder) : []),
    [ladder],
  );
  const exchange =
    ladder?.exchange.toLowerCase() === Exchange.KUCOIN
      ? Exchange.KUCOIN
      : Exchange.BINANCE;
  const chartSymbol = ladder ? chartSymbolForLadder(ladder) : "";
  const gridReturnPct = ladder ? calculateGridReturnPct(ladder) : 0;

  if (!ladder) {
    return <Container fluid>Grid ladder not found.</Container>;
  }

  return (
    <div className="content">
      <Container fluid>
        <Row>
          <Col md="12" sm="12">
            <Card
              style={{
                display: "flex",
                flexDirection: "column",
                minHeight: "580px",
              }}
            >
              <Card.Header>
                <div className="d-flex justify-content-between align-items-center">
                  <Card.Title as="h3" className="mb-0">
                    {ladder.symbol}{" "}
                    <Badge
                      bg={returnBadgeBg(gridReturnPct)}
                      className={prominentBadgeClass}
                    >
                      {gridReturnPct}%
                    </Badge>{" "}
                    {ladder.exchange}/{ladder.market_type}
                  </Card.Title>
                  <Badge
                    bg={statusBadgeBg(ladder.status)}
                    className={prominentBadgeClass}
                  >
                    {ladder.status}
                  </Badge>
                </div>
              </Card.Header>
              <Card.Body
                style={{ flex: 1, display: "flex", flexDirection: "column" }}
              >
                <TVChartContainer
                  symbol={chartSymbol}
                  interval={"1h" as ResolutionString}
                  timescaleMarks={[]}
                  orderLines={orderLines}
                  exchange={exchange}
                  style={{ minHeight: "100%", height: "600px", width: "100%" }}
                />
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Row>
          <Col md="7" sm="12">
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <h3 className="mb-0">Grid Ladder</h3>
              </Card.Header>
              <Card.Body>
                <Row className="mb-2">
                  <Col md={4}>
                    <strong>Algorithm</strong>
                  </Col>
                  <Col md={8}>{ladder.algorithm_name}</Col>
                </Row>
                <Row className="mb-2">
                  <Col md={4}>
                    <strong>Range</strong>
                  </Col>
                  <Col md={8}>
                    {ladder.range_low} → {ladder.range_high}
                  </Col>
                </Row>
                <Row className="mb-2">
                  <Col md={4}>
                    <strong>Breakout</strong>
                  </Col>
                  <Col md={8}>
                    {ladder.breakout_low} / {ladder.breakout_high}
                  </Col>
                </Row>
                {ladder.orders.length > 0 && (
                  <>
                    <h4 className="mt-4 mb-3">Orders</h4>
                    <Row className="g-2 mb-3">
                      {ladder.orders.map((order) => (
                        <Col key={order.id} lg={6}>
                          <Card className="h-100">
                            <Card.Body>
                              <div className="d-flex justify-content-between">
                                <strong>{order.order_role}</strong>
                                <Badge
                                  bg={statusBadgeBg(order.status)}
                                  className={prominentBadgeClass}
                                >
                                  {order.status ?? "-"}
                                </Badge>
                              </div>
                              <div className="small mt-2">
                                Exchange order: {order.exchange_order_id}
                              </div>
                              <div className="small">
                                Side: {order.side ?? "-"}
                              </div>
                              <div className="small">
                                Price: {order.price ?? "-"}
                              </div>
                              <div className="small">
                                Contracts: {order.contracts}
                              </div>
                              <div className="small">
                                Filled: {order.filled_qty}
                                {order.filled_price
                                  ? ` @ ${order.filled_price}`
                                  : ""}
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </>
                )}
                <Row className="g-2 mt-2">
                  {ladder.levels.map((level) => (
                    <Col key={level.id} lg={6}>
                      <Card className="h-100">
                        <Card.Body>
                          <div className="d-flex justify-content-between">
                            <strong>Level #{level.level_index}</strong>
                            <Badge
                              bg={statusBadgeBg(level.status)}
                              className={prominentBadgeClass}
                            >
                              {level.status}
                            </Badge>
                          </div>
                          <div className="small mt-2">Price: {level.price}</div>
                          <div className="small">Side: {level.side}</div>
                          <div className="small">
                            Contracts: {level.contracts}
                          </div>
                          <div className="small">
                            Filled Qty: {level.filled_entry_qty}
                          </div>
                          <div className="small">
                            TP: {level.take_profit_price ?? "-"}
                          </div>
                          <div className="small">
                            Realized PnL: {level.realized_pnl}
                          </div>
                        </Card.Body>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card.Body>
            </Card>
          </Col>
          <Col md="5" sm="12">
            <Card>
              <Card.Header>
                <h3 className="mb-0">Logs</h3>
              </Card.Header>
              <Card.Body>
                {ladder.logs && ladder.logs.length > 0 ? (
                  <pre
                    className="small bg-light p-2 rounded mb-0"
                    style={{
                      maxHeight: "420px",
                      overflow: "auto",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {ladder.logs.map(formatLogEntry).join("\n\n")}
                  </pre>
                ) : (
                  <p className="mb-0">No logs recorded.</p>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default GridLadderDetail;
