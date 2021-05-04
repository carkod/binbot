import React from "react";
import { Card, CardBody, CardHeader, CardTitle } from "reactstrap";

export default function Deal({ bot }) {
  const so = Object.values(bot.safety_orders)[0];
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Active deal</CardTitle>
      </CardHeader>
      <CardBody>
        {`Take Profit ${parseFloat(bot.deal.buy_price) * (1 + parseFloat(bot.take_profit))}`}
        {`Base ${bot.deal.buy_price}`}{" "}
        {`Safety order ${(parseFloat(bot.deal.buy_price) * parseFloat(so.price_deviation_so)) - parseFloat(bot.deal.buy_price)}`}{" "}
      </CardBody>
    </Card>
  );
}
