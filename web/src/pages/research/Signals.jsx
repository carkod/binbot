import React from "react";
import { Table, TabPane } from "reactstrap";

export default function Signals({ data }) {
  return (
    <Table hover>
      <thead>
        <tr>
          <th>Market</th>
          <th>Price</th>
          <th>Signal</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item, i) => (
          <tr key={i}>
            <th scope="row">{item.market_a}</th>
            <td>{item.current_price}</td>
            <td
              className={
                item.bollinguer_bands_signal === "BUY"
                  ? "u-td-bg-color--success"
                  : item.bollinguer_bands_signal === "SELL"
                  ? "u-td-bg-color--danger"
                  : "u-td-bg-color--disabled"
              }
            >
              {item.bollinguer_bands_signal}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
