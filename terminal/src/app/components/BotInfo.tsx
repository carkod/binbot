import { useState } from "react";
import {
  Button,
  Card,
  ListGroup,
  ListGroupItem,
  Table,
  Row,
  Col,
  Container,
} from "react-bootstrap";
import { formatTimestamp } from "./RenderTs";
import { renderDuration } from "../../utils/time";

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
            {bot.orders.length > 0 && (
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
            )}
          </Table>
          {bot.deal && (
            <Container>
              <Row>
                <Col>
                  <h5>Deal information (representated in the graph)</h5>
                </Col>
              </Row>
              <Row>
                <Col xl="8" lg="12">
                  <ListGroup>
                    {Object.keys(bot.deal).map((k, i) => {
                      if (typeof bot.deal[k] !== "object") {
                        let dealData = bot.deal[k];
                        if (k === "buy_timestamp" || k === "sell_timestamp") {
                          dealData =
                            bot.deal[k] === 0 || formatTimestamp(bot.deal[k]);
                        }
                        return (
                          <ListGroupItem
                            key={i}
                            className="d-flex justify-content-between align-items-start"
                          >
                            <strong>{k}</strong> {dealData}
                          </ListGroupItem>
                        );
                      } else {
                        return (
                          <ListGroup key={i}>
                            {Object.keys(bot.deal[k]).map((l, j) => (
                              <ListGroupItem key={j}>
                                {l}:{bot.deal[k][l]}
                              </ListGroupItem>
                            ))}
                          </ListGroup>
                        );
                      }
                    })}
                    <ListGroupItem className="d-flex justify-content-between align-items-start">
                      <strong>duration</strong>
                      <p className="small">{renderDuration(bot)}</p>
                    </ListGroupItem>
                  </ListGroup>
                </Col>
              </Row>
            </Container>
          )}
        </Card.Body>
      )}
    </Card>
  );
}
