import React from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  ListGroup,
  ListGroupItem,
  Table,
} from "reactstrap";
import { checkValue } from "../validations";
import moment from "moment";
import { botDuration } from "../state/bots/actions";

const renderSellTimestamp = (bot) => {
  if (!checkValue(bot.deal?.buy_timestamp)) {
    let sell_timestamp = new Date();
    if (!checkValue(bot.deal.sell_timestamp)) {
      sell_timestamp = bot.deal.sell_timestamp;
      return (
        <ListGroupItem className="d-flex justify-content-between align-items-start">
          <strong>duration</strong>
          {sell_timestamp === 0
            ? botDuration(bot.deal.buy_timestamp, new Date().getTime())
            : botDuration(bot.deal.buy_timestamp, sell_timestamp)}
        </ListGroupItem>
      );
    }
  }
  return "";
};

export default function BotInfo({ bot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Orders information</CardTitle>
      </CardHeader>
      <CardBody>
        <Table responsive>
          <thead>
            <tr>
              <th>Order Id</th>
              <th>Deal type</th>
              <th>Price</th>
              <th>Qty</th>
              <th>Status</th>
              <th>Order Side</th>
            </tr>
          </thead>
          {bot.orders.length > 0 && (
            <tbody>
              {bot.orders.map((deal, i) => {
                if (typeof deal === "object" && "deal_type" in deal) {
                  return (
                    <tr key={deal.order_id}>
                      <th scope="row">{deal.order_id}</th>
                      <td>{deal.deal_type}</td>
                      <td>{deal.price}</td>
                      <td>{parseFloat(deal.qty)}</td>
                      <td>{deal.status}</td>
                      <td>{deal.order_side}</td>
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
        <hr />
        {!checkValue(bot.deal) && !checkValue(bot.deal.buy_price) && (
          <div className="col-6">
            <h5>Deal information (representated in the graph)</h5>
            <ListGroup>
              {Object.keys(bot.deal).map((k, i) => {
                if (typeof bot.deal[k] !== "object") {
                  let dealData = bot.deal[k];
                  if (k === "buy_timestamp" || k === "sell_timestamp") {
                    dealData =
                      bot.deal[k] === 0 ||
                      moment(bot.deal[k]).format("D MMM, HH:mm");
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
              {renderSellTimestamp(bot)}
            </ListGroup>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
