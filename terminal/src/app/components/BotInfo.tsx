import { useState } from "react";
import {
  Button,
  Card,
  ListGroup,
  Table,
  Container,
  Badge,
  Nav,
  Tab,
} from "react-bootstrap";
import { renderDuration, formatTimestamp } from "../../utils/time";
import type { Bot } from "../../features/bots/botInitialState";

interface BotInfoProps {
  bot: Bot;
}

export default function BotInfo({ bot }: BotInfoProps) {
  const [isExpanded, setExpanded] = useState<boolean>(bot.orders?.length > 0);
  return (
    <Tab.Container
      defaultActiveKey="orders"
      mountOnEnter
      unmountOnExit
      transition={false}
    >
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <Card.Title as="h5">Bot information</Card.Title>
          <Button
            onClick={() => setExpanded(!isExpanded)}
            className="u-float-right u-space-bottom"
            aria-expanded={isExpanded}
          >
            {isExpanded ? "Hide" : "Show"}
          </Button>
        </Card.Header>
        {isExpanded && (
          <Card.Body>
            <Nav variant="tabs">
              <Nav.Item>
                <Nav.Link eventKey="orders">Orders information</Nav.Link>
              </Nav.Item>
              <Nav.Item>
                <Nav.Link eventKey="deal">Deal information</Nav.Link>
              </Nav.Item>
            </Nav>
            <Tab.Content>
              <Tab.Pane eventKey="orders">
                {bot.orders.length > 0 && (
                  <Table responsive>
                    <thead>
                      <tr>
                        <th>Order Id</th>
                        <th>Timestamp</th>
                        <th>Deal type</th>
                        <th>Order type</th>
                        <th>Price</th>
                        <th>Qty</th>
                        <th>Status</th>
                        <th>Order Side</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bot.orders.map((order, i) => {
                        if (
                          typeof order === "object" &&
                          "order_type" in order
                        ) {
                          return (
                            <tr key={order.order_id}>
                              <th scope="row">{order.order_id}</th>
                              <td>
                                {formatTimestamp(parseFloat(order.timestamp))}
                              </td>
                              <td>{order.deal_type}</td>
                              <td>{order.order_type}</td>
                              <td>{order.price}</td>
                              <td>{parseFloat(order.qty)}</td>
                              <td>{order.status}</td>
                              <td>{order.order_side}</td>
                            </tr>
                          );
                        }
                        return (
                          <tr key={i}>
                            <td></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </Table>
                )}
              </Tab.Pane>
              <Tab.Pane eventKey="deal">
                {bot.deal && (
                  <Container>
                    <footer className="blockquote-footer">
                      <p>Represented in the chart</p>
                    </footer>
                    <ListGroup className="list-group-flush">
                      {Object.keys(bot.deal)
                        .filter((k) => k !== "conditional_close_order")
                        .map((k, i) => {
                          let dealData = bot.deal[k];
                          if (
                            k === "opening_timestamp" ||
                            k === "closing_timestamp"
                          ) {
                            dealData =
                              bot.deal[k] === 0 || formatTimestamp(bot.deal[k]);
                          }
                          if (
                            dealData !== null &&
                            typeof dealData === "object"
                          ) {
                            dealData = JSON.stringify(dealData);
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
              </Tab.Pane>
            </Tab.Content>
          </Card.Body>
        )}
      </Card>
    </Tab.Container>
  );
}
