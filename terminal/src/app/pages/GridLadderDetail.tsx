import type { FC } from "react";
import { Badge, Card, Col, Container, Row } from "react-bootstrap";
import { useParams } from "react-router";
import { useGetGridLadderQuery } from "../../features/gridLadders/gridLaddersApiSlice";

const GridLadderDetail: FC = () => {
  const { id = "" } = useParams();
  const { data: ladder } = useGetGridLadderQuery(id, { skip: !id, refetchOnFocus: true });

  if (!ladder) {
    return <Container fluid>Grid ladder not found.</Container>;
  }

  return (
    <Container fluid>
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h3 className="mb-0">{ladder.symbol} Grid Ladder</h3>
          <Badge bg="secondary">{ladder.status}</Badge>
        </Card.Header>
        <Card.Body>
          <Row className="mb-2">
            <Col md={4}><strong>Algorithm</strong></Col>
            <Col md={8}>{ladder.algorithm_name}</Col>
          </Row>
          <Row className="mb-2">
            <Col md={4}><strong>Range</strong></Col>
            <Col md={8}>{ladder.range_low} → {ladder.range_high}</Col>
          </Row>
          <Row className="mb-2">
            <Col md={4}><strong>Breakout</strong></Col>
            <Col md={8}>{ladder.breakout_low} / {ladder.breakout_high}</Col>
          </Row>
          <Row className="g-2 mt-2">
            {ladder.levels.map((level) => (
              <Col key={level.id} lg={6}>
                <Card className="h-100">
                  <Card.Body>
                    <div className="d-flex justify-content-between">
                      <strong>Level #{level.level_index}</strong>
                      <Badge bg={level.filled_entry_qty > 0 ? "success" : "secondary"}>{level.status}</Badge>
                    </div>
                    <div className="small mt-2">Price: {level.price}</div>
                    <div className="small">Side: {level.side}</div>
                    <div className="small">Contracts: {level.contracts}</div>
                    <div className="small">Filled Qty: {level.filled_entry_qty}</div>
                    <div className="small">TP: {level.take_profit_price ?? "-"}</div>
                    <div className="small">Realized PnL: {level.realized_pnl}</div>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default GridLadderDetail;
