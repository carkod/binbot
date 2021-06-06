import React from "react";
import { Button, Table } from "reactstrap";
import moment from "moment";
import { roundDecimals } from "../../validations";

export default function Signals({ data, setPair }) {
  return (
    <Table hover>
      <thead>
        <tr>
          <th>Market</th>
          <th>Signal</th>
          <th>Spread (L vs H)</th>
          <th>Last Volume</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item, i) => (
          <tr key={i}>
            <th scope="row">
            <button className="btn-reset" onClick={() => setPair(item.market_a)}>{item.market_a}</button>
            </th>
            <td
              className={
                item.bollinguer_bands_signal === "STRONG BUY" ||
                item.bollinguer_bands_signal === "WEAK BUY"
                  ? "u-td-bg-color--success"
                  : item.bollinguer_bands_signal === "STRONG SELL" ||
                    item.bollinguer_bands_signal === "WEAK SELL"
                  ? "u-td-bg-color--danger"
                  : "u-td-bg-color--disabled"
              }
            >
              {item.bollinguer_bands_signal}
              <br />
              {item.lastModified &&
                <small>{moment(item.lastModified.$date).fromNow()}</small>
              }
            </td>
            <td>{item.spread}</td>
            <td>{roundDecimals(item.last_volume, 4)}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
