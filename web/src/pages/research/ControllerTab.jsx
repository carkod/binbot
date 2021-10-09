import React from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  FormGroup,
  Input,
  Label,
  Row,
} from "reactstrap";

const CandlestickIntervalForm = ({
  candlestickInterval,
  handleCandlestickInterval,
}) => {
  return (
    <FormGroup>
      <Label for="controller_candlestick_interval">Candlestick interval</Label>
      <Input
        type="input"
        name="controller_candlestick_interval"
        id="candlestick-interval"
        onChange={handleCandlestickInterval}
        defaultValue={candlestickInterval}
      />
    </FormGroup>
  );
};

export const ControllerTab = ({ blacklistData, symbols, candlestickInterval, handleInput }) => {
  return (
    <>
      <Row>
        <Col md="12" sm="3">
          <Card>
            <CardHeader>
              <CardTitle>General settings for research signals</CardTitle>
            </CardHeader>
            <CardBody>
              <Row>
                <Col md="!2">
                  <CandlestickIntervalForm
                    candlestickInterval={candlestickInterval}
                    handleInput={handleInput}
                  />
                </Col>
              </Row>
              <Row>
                <Col md="6">
                  <FormGroup>
                    <Label for="blacklist">View blacklisted</Label>
                    <Input
                      type="text"
                      name="blacklist"
                      id="blacklisted"
                      readOnly="true"
                    >
                      {blacklistData.map((x, i) => (
                        <option key={i} value={x}>
                          x
                        </option>
                      ))}
                    </Input>
                  </FormGroup>
                </Col>
                <Col md="6">
                  <FormGroup>
                    {/* <SymbolSearch
                      name="blacklisted_pair"
                      label="Add new blacklisted coin"
                      options={symbols}
                      selected={null}
                      handleChange={handlePairChange}
                    /> */}
                  </FormGroup>
                </Col>
              </Row>
            </CardBody>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default ControllerTab;
