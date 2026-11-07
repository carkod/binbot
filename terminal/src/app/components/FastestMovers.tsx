import { Badge, Card, Col, ListGroup, Row } from "react-bootstrap";
import type {
  FastestMover,
  FastestMoversSnapshot,
} from "../../features/marketApiSlice";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";

function MoverList({
  title,
  movers,
}: {
  title: string;
  movers: FastestMover[];
}) {
  return (
    <Card.Body>
      <Card.Title>{title}</Card.Title>
      <ListGroup className="list-group-flush">
        {movers.map((mover) => (
          <ListGroup.Item key={mover.symbol}>
            <span className="text-break">{mover.symbol}</span>
            <Badge
              bg={mover.price_change_1h_percent > 0 ? "success" : "danger"}
              className="u-float-right"
            >
              {roundDecimals(mover.price_change_1h_percent, 2)}% in 1h
            </Badge>
            {mover.price_change_3h_percent !== null && (
              <div className="text-body-secondary small">
                3h: {roundDecimals(mover.price_change_3h_percent, 2)}%
              </div>
            )}
          </ListGroup.Item>
        ))}
      </ListGroup>
    </Card.Body>
  );
}

export default function FastestMovers({
  data,
}: {
  data: FastestMoversSnapshot | undefined;
}) {
  return (
    <Card border="success">
      <Card.Header>
        Fastest futures movers
        {data?.recorded_at && (
          <small className="text-body-secondary ms-2">
            As of {formatTimestamp(data.recorded_at)}
          </small>
        )}
      </Card.Header>
      {data?.comparison_at ? (
        <Row className="g-0">
          <Col>
            <MoverList title="Rising (1h)" movers={data.gainers} />
          </Col>
          <Col>
            <MoverList title="Falling (1h)" movers={data.losers} />
          </Col>
        </Row>
      ) : (
        <Card.Body>
          Waiting for futures price snapshots one hour apart.
        </Card.Body>
      )}
    </Card>
  );
}
