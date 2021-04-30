import React from "react";
import { Card, CardBody, CardHeader, CardTitle, Table } from "reactstrap";

export default function BotInfo({ bot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Bot Information</CardTitle>
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
            {bot.deals.map((deal) => {
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
              }
            })}
          </tbody>
        </Table>
      </CardBody>
    </Card>
  );
}
