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
                    {ladder.symbol} Grid Ladder
                  </Card.Title>
                  <Badge bg="secondary">{ladder.status}</Badge>
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

        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h3 className="mb-0">{ladder.symbol} Grid Ladder</h3>
            <Badge bg="secondary">{ladder.status}</Badge>
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
            <Row className="g-2 mt-2">
              {ladder.levels.map((level) => (
                <Col key={level.id} lg={6}>
                  <Card className="h-100">
                    <Card.Body>
                      <div className="d-flex justify-content-between">
                        <strong>Level #{level.level_index}</strong>
                        <Badge
                          bg={
                            level.filled_entry_qty > 0 ? "success" : "secondary"
                          }
                        >
                          {level.status}
                        </Badge>
                      </div>
                      <div className="small mt-2">Price: {level.price}</div>
                      <div className="small">Side: {level.side}</div>
                      <div className="small">Contracts: {level.contracts}</div>
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
      </Container>
    </div>
  );
};

export default GridLadderDetail;
