
import React from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  FormGroup,
  Label,
  Input,
  Row,
} from "reactstrap";
import Candlestick from "../../components/Candlestick";
import { checkValue, intervalOptions } from "../../validations";
import Signals from "../../components/Signals";


const filterStrengthOptions = ["ALL", "STRONG", "WEAK"];
const filterSideOptions = ["ALL", "BUY", "SELL"];
const filterCandlestickSignalOptions = ["ALL", "positive", "negative"];

export default function SignalsTab({ candlestick, pair, candlestick_interval, strengthFilter, research, sideFilter, candlestickSignalFilter, handleInterval, handleSignalsFilter, handleSetPair, handleSignalsOrder }) {
  return (
    <>
      {pair && (
        <Row>
          <Col md="12">
            <Card style={{ minHeight: "650px" }}>
              <CardHeader>
                <CardTitle tag="h3">{pair}</CardTitle>
                Interval: {candlestick_interval}
              </CardHeader>
              <CardBody>
                {candlestick && !checkValue(pair) ? (
                  <Candlestick data={candlestick} />
                ) : (
                  ""
                )}
              </CardBody>
            </Card>
          </Col>
        </Row>
      )}
      <Row>
        <Col md="12" sm="3">
          <Card>
            <CardHeader>
              <CardTitle>
                <Row>
                  <Col md="3">
                    <FormGroup>
                      <Label for="candlestick_interval">Select Interval</Label>
                      <Input
                        type="select"
                        name="candlestick_interval"
                        id="interval"
                        onChange={handleInterval}
                        defaultValue={candlestick_interval}
                      >
                        {intervalOptions.map((x, i) => (
                          <option key={x} value={x}>
                            {x}
                          </option>
                        ))}
                      </Input>
                    </FormGroup>
                  </Col>
                  <Col md="3">
                    <FormGroup>
                      <Label for="strengthFilter">Filter by strength:</Label>
                      <Input
                        type="select"
                        name="strengthFilter"
                        id="strength-filter"
                        onChange={handleSignalsFilter}
                        defaultValue={strengthFilter}
                      >
                        {filterStrengthOptions.map((x, i) => (
                          <option key={i} value={x}>
                            {x}
                          </option>
                        ))}
                      </Input>
                    </FormGroup>
                  </Col>
                  <Col md="3">
                    <FormGroup>
                      <Label for="sideFilter">Filter by side:</Label>
                      <Input
                        type="select"
                        name="sideFilter"
                        id="side-filter"
                        onChange={handleSignalsFilter}
                        defaultValue={sideFilter}
                      >
                        {filterSideOptions.map((x, i) => (
                          <option key={i} value={x}>
                            {x}
                          </option>
                        ))}
                      </Input>
                    </FormGroup>
                  </Col>
                  <Col md="3">
                    <FormGroup>
                      <Label for="candlestickSignalFilter">Filter by candlestick signal:</Label>
                      <Input
                        type="select"
                        name="candlestickSignalFilter"
                        id="candlestick-signal-filter"
                        onChange={handleSignalsFilter}
                        defaultValue={candlestickSignalFilter}
                      >
                        {filterCandlestickSignalOptions.map((x, i) => (
                          <option key={i} value={x}>
                            {x}
                          </option>
                        ))}
                      </Input>
                    </FormGroup>
                  </Col>
                </Row>
              </CardTitle>
            </CardHeader>
            <CardBody>
              {research && research.length > 0 ? (
                <Signals
                  data={research}
                  setPair={handleSetPair}
                  orderBy={handleSignalsOrder}
                />
              ) : (
                "No signals available"
              )}
            </CardBody>
          </Card>
        </Col>
      </Row>
    </>
  );
}
