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
          <ListGroup.Item
            key={mover.symbol}
            className="d-flex justify-content-between align-items-start gap-2"
          >
            <Card.Link
              href={`/bots/futures/new/${mover.symbol}`}
              className="text-break"
            >
              {mover.symbol}
            </Card.Link>
            <div className="d-flex flex-column align-items-end gap-1 flex-shrink-0">
              <Badge
                bg={mover.price_change_1h_percent > 0 ? "success" : "danger"}
              >
                {roundDecimals(mover.price_change_1h_percent, 2)}% in 1h
              </Badge>
              {mover.price_change_3h_percent !== null && (
                <Badge
                  bg={mover.price_change_3h_percent > 0 ? "success" : "danger"}
                >
                  {roundDecimals(mover.price_change_3h_percent, 2)}% in 3h
                </Badge>
              )}
            </div>
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
            <MoverList title="Rising" movers={data.gainers} />
          </Col>
          <Col>
            <MoverList title="Falling" movers={data.losers} />
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
