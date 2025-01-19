import { useState } from "react";
import {
  Button,
  Card,
  ListGroup,
  Table,
  Row,
  Col,
  Container,
  Badge,
} from "react-bootstrap";
import { renderDuration, formatTimestamp } from "../../utils/time";

export default function BotInfo({ bot }) {
  const [showOrderInfo, toggleOrderInfo] = useState<boolean>(
    bot.orders?.length > 0,
  );
  return (
    <Card>
      <Card.Header className="u-space-between">
        <Card.Title as="h5">Orders information</Card.Title>
        <Button
          onClick={() => toggleOrderInfo(!showOrderInfo)}
          className="u-float-right u-space-bottom"
        >
          Hide
        </Button>
      </Card.Header>
      {showOrderInfo && (
        <Card.Body>
          {bot.orders.length > 0 && (
            <Table responsive>
              <thead>
                <tr>
                  <th>Order Id</th>
                  <th>Timestamp</th>
                  <th>Deal type</th>
                  <th>Price</th>
                  <th>Qty</th>
                  <th>Status</th>
                  <th>Order Side</th>
                </tr>
              </thead>
              <tbody>
                {bot.orders.map((order, i) => {
                  if (typeof order === "object" && "order_type" in order) {
                    return (
                      <tr key={order.order_id}>
                        <th scope="row">{order.order_id}</th>
                        <td>{formatTimestamp(parseFloat(order.timestamp))}</td>
                        <td>{order.order_type}</td>
                        <td>{order.price}</td>
                        <td>{parseFloat(order.qty)}</td>
                        <td>{order.status}</td>
                        <td>{order.order_side}</td>
                      </tr>
                    );
                  } else {
                    return (
                      <tr key={i}>
                        <td></td>
                      </tr>
                    );
                  }
                })}
              </tbody>
            </Table>
          )}
          {bot.deal && (
            <Container>
              <Row>
                <Col>
                  <Card.Subtitle className="mb-2 text-muted upper">
                    Deal information
                  </Card.Subtitle>
                  <footer className="blockquote-footer">
                    <p>representated in the graph</p>
                  </footer>
                </Col>
              </Row>
              <ListGroup className="list-group-flush">
                {Object.keys(bot.deal).map((k, i) => {
                  if (typeof bot.deal[k] !== "object") {
                    let dealData = bot.deal[k];
                    if (k === "buy_timestamp" || k === "sell_timestamp") {
                      dealData =
                        bot.deal[k] === 0 || formatTimestamp(bot.deal[k]);
                    }
                    return (
                      <ListGroup.Item
                        action
                        as="h5"
                        key={i}
                        className="d-flex justify-content-between align-items-start"
                      >
                        <small>{k}</small>
                        {dealData || dealData > 0 ? (
                          <Badge bg="secondary">{dealData}</Badge>
                        ) : (
                          <small>{dealData}</small>
                        )}
                      </ListGroup.Item>
                    );
                  } else {
                    return (
                      <ListGroup key={i} variant="flush">
                        {Object.keys(bot.deal[k]).map((l, j) => (
                          <ListGroup.Item
                            key={j}
                            as="h5"
                            className="d-flex justify-content-between align-items-start"
                          >
                            <div className="ms-2 me-auto">
                              {l}:{bot.deal[k][l]}
                            </div>
                          </ListGroup.Item>
                        ))}
                      </ListGroup>
                    );
                  }
                })}
                <ListGroup.Item
                  as="h5"
                  className="d-flex justify-content-between align-items-start"
                >
                  <small>deal duration</small>
                  <Badge bg="secondary">{renderDuration(bot)}</Badge>
                </ListGroup.Item>
              </ListGroup>
            </Container>
          )}
        </Card.Body>
      )}
    </Card>
  );
}
