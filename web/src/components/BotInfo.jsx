import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Table } from "reactstrap";
import { checkValue } from "../validations";
  

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
          <tbody>
            {bot.orders.map((deal) => {
              if (typeof deal === "object" && "deal_type" in deal) {
                return (
                  <tr key={deal.order_id}>
                    <th scope="row">{deal.order_id}</th>
                    <td>{deal.deal_type}</td>
                    <td>{deal.price}</td>
                    <td>{parseInt(deal.qty)}</td>
                    <td>{deal.status}</td>
                    <td>{deal.order_side}</td>
                  </tr>
                );
              } else {
                return ("")
              }
            })}
          </tbody>
        </Table>
        <hr />
        {!checkValue(bot.deal) && !checkValue(bot.deal.buy_price) && (
          <>
          <h5>Deal information (representated in the graph)</h5>
          <ul>
            {Object.keys(bot.deal).map((k, i) => {
              if (typeof(bot.deal[k]) !== "object") {
                return <li key={i}><strong>{k}</strong>: {bot.deal[k]}</li>
              } else {
                return (
                  <ul>
                    {Object.keys(bot.deal[k]).map((l,j) => <li key={j}>{l}:{bot.deal[k][l]}</li>)}
                  </ul>
                )
              }
            } )}
          </ul>
          </>
        )}
      </CardBody>
    </Card>
  );
}
