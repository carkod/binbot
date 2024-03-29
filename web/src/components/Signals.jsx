import moment from "moment";
import React from "react";
import { Table } from "reactstrap";
import { checkValue, roundDecimals } from "../validations";

export default function Signals({ data, setPair, orderBy }) {
  return (
    <Table hover>
      <thead>
        <tr>
          <th>Market</th>
          <th>Signal</th>
          <th>
            <button className="btn-reset" onClick={() => orderBy("spread")}>
              Spread (L vs H)
            </button>
          </th>
          <th>
            <button className="btn-reset" onClick={() => orderBy("volume")}>
              Last Volume
            </button>
          </th>
          <th>
            <button className="btn-reset" onClick={() => orderBy("price_change_24")}>
            24hr Change
            </button>
          </th>
          <th>
            Candle jump
          </th>
        </tr>
      </thead>
      <tbody>
        {data.map((item, i) => (
          <tr key={i}>
            <th scope="row">
              <button
                className="btn-reset"
                onClick={() => setPair(item.market)}
              >
                {item.market}
              </button>
            </th>
            <td
              className={
                !checkValue(item.signal_side) && item.signal_side === "BUY"
                  ? "u-td-bg-color--success"
                  : item.signal_side === "SELL"
                  ? "u-td-bg-color--danger"
                  : "u-td-bg-color--disabled"
              }
            >
              {`${item.signal_strength} ${item.signal_side}`}
              <br />
              {item.lastModified && (
                <small>{moment(item.lastModified.$date).fromNow()}</small>
              )}
            </td>
            <td>{roundDecimals(item.spread * 100, 4) + "%"}</td>
            <td>{roundDecimals(item.last_volume, 4)}</td>
            <td>{!checkValue(item.price_change_24) ? item.price_change_24 + "%" : ""}</td>
            <td
              className={
                item.candlestick_signal === "positive"
                  ? "u-td-bg-color--success"
                  : item.candlestick_signal === "negative"
                  ? "u-td-bg-color--danger"
                  : "u-td-bg-color--disabled"
              }
            ></td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
