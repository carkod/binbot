import type { FC } from "react";
import { Badge, Button, Card, Col, Row } from "react-bootstrap";
import { useNavigate } from "react-router";
import {
  calculateFilledLevelCount,
  calculateGridPnl,
  calculateGridUtilization,
  calculateOpenOrderCount,
  type GridLadder,
} from "../../features/gridLadders/gridLadders";
import type { GridLadderStatus } from "../../features/gridLadders/gridLadders";
import { returnBadgeBg } from "../../utils/grid-ladder";

interface GridLadderCardProps {
  ladder: GridLadder;
  gridReturnPct: number;
  selected: boolean;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}

const statusColorMap: Record<GridLadderStatus, string> = {
  pending: "secondary",
  active: "success",
  closing: "warning",
  closed: "dark",
  range_broken: "danger",
  error: "danger",
};

const GridLadderCard: FC<GridLadderCardProps> = ({
  ladder,
  gridReturnPct,
  selected,
  onSelect,
  onClose,
}) => {
  const navigate = useNavigate();
  const totalPnl = calculateGridPnl(ladder);
  const utilization = calculateGridUtilization(ladder);

  return (
    <Card className={selected ? "border border-success" : ""}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <strong>{ladder.symbol}</strong>
          <div className="text-muted small">{ladder.algorithm_name}</div>
        </div>
        <div className="d-flex flex-column align-items-end gap-1">
          <Badge bg={statusColorMap[ladder.status]}>
            {ladder.status.toUpperCase()}
          </Badge>
          <Badge bg={returnBadgeBg(gridReturnPct)}>{gridReturnPct}%</Badge>
        </div>
      </Card.Header>
      <Card.Body>
        <div className="small text-muted mb-2">
          {ladder.exchange} / {ladder.market_type}
        </div>
        <Row>
          <Col xs={6}>Range</Col>
          <Col xs={6} className="text-end">
            {ladder.range_low} → {ladder.range_high}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>Breakout</Col>
          <Col xs={6} className="text-end">
            {ladder.breakout_low} / {ladder.breakout_high}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>Levels</Col>
          <Col xs={6} className="text-end">
            {ladder.level_count}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>Step</Col>
          <Col xs={6} className="text-end">
            {ladder.grid_step}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>Margin</Col>
          <Col xs={6} className="text-end">
            {ladder.reserved_margin} / {ladder.total_margin}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>PnL</Col>
          <Col
            xs={6}
            className={`text-end ${totalPnl >= 0 ? "text-success" : "text-danger"}`}
          >
            {totalPnl.toFixed(4)}
          </Col>
        </Row>
        <Row>
          <Col xs={6}>Utilization</Col>
          <Col xs={6} className="text-end">
            {utilization.toFixed(2)}%
          </Col>
        </Row>
        <hr />
        <div className="small">
          Open orders: {calculateOpenOrderCount(ladder)} · Filled levels:{" "}
          {calculateFilledLevelCount(ladder)}
        </div>
        <div className="d-flex flex-column gap-1 mt-2">
          {ladder.levels.map((level, index) => {
            const isFilled = level.filled_entry_qty > 0;
            const tone =
              index < ladder.levels.length / 2
                ? "text-danger"
                : index > ladder.levels.length / 2
                  ? "text-success"
                  : "text-secondary";
            return (
              <div
                key={level.id}
                className={`border rounded p-1 small ${isFilled ? "border-2" : ""}`}
              >
                <span className={tone}>
                  #{level.level_index} {level.side}
                </span>{" "}
                @ {level.price} · c:{level.contracts} · tp:
                {level.take_profit_price ?? "-"} · pnl:{level.realized_pnl}
              </div>
            );
          })}
        </div>
      </Card.Body>
      <Card.Footer className="d-flex justify-content-between">
        <Button
          variant="info"
          onClick={() => navigate(`/grid-ladders/${ladder.id}`)}
        >
          View details
        </Button>
        <Button variant="warning" onClick={() => onSelect(ladder.id)}>
          {selected ? "Unselect" : "Select"}
        </Button>
        <Button variant="danger" onClick={() => onClose(ladder.id)}>
          Close ladder
        </Button>
      </Card.Footer>
    </Card>
  );
};

export default GridLadderCard;
