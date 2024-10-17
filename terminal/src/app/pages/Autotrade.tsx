import { type FC } from "react"
import { useAppDispatch } from "../hooks"
import { Button, Card, Col, Row } from "react-bootstrap"
import { useGetSettingsQuery } from "../../features/autotradeApiSlice"
import SettingsInput from "../components/SettingsInput"
import LightSwitch from "../components/LightSwitch"

export const AutotradePage: FC<{}> = () => {
  const dispatch = useAppDispatch()

  const { data } = useGetSettingsQuery()

  return (
    <Card>
      {console.log(data)}
      <Card.Header>
        <Card.Title>Bot Autotrade settings</Card.Title>
      </Card.Header>
      <Card.Body>
        <Row>
          <Col md={"12"} sm="12">
            <Row>
              <Col md="3">
                <SettingsInput
                  value={data.candlestick_interval}
                  name={"candlestick_interval"}
                  label={"Candlestick interval"}
                  handleChange={handleInput}
                />
              </Col>

              <Col md="3">
                <label htmlFor="telegram_signals">
                  Send messages to telegram?
                </label>
                <br />
                <LightSwitch
                  value={data.telegram_signals}
                  name="telegram_signals"
                  toggle={toggle}
                />
              </Col>
              <Col md="3">
                <label htmlFor="strategy">Strategy</label>
                <Form.Select
                  size="sm"
                  name="strategy"
                  onChange={handleInput}
                  value={data.strategy}
                >
                  <option value="long">Long</option>
                  <option value="margin_long">Margin long</option>
                  <option value="margin_short">Margin short</option>
                </Form.Select>
              </Col>
            </Row>
            <Row>
              <Col md="3">
                <label htmlFor="autotrade">Autotrade?</label>
                <br />
                <LightSwitch
                  value={data.autotrade}
                  name="autotrade"
                  toggle={toggle}
                />
              </Col>
              <Col md="3">
                <SettingsInput
                  value={data.max_active_autotrade_bots}
                  name={"max_active_autotrade_bots"}
                  label={"Max active autotrade bots"}
                  handleChange={handleInput}
                />
              </Col>
            </Row>
            <Row>
              <Col md="3">
                <label htmlFor="trailling">Trailling</label>
                <br />
                <Button
                  name="trailling"
                  color={data.trailling === "true" ? "success" : "secondary"}
                  onClick={toggleTrailling}
                >
                  {data.trailling === "true" ? "On" : "Off"}
                </Button>
              </Col>
              {data.trailling === "true" && (
                <>
                  <Col md="3">
                    <SettingsInput
                      value={data.base_order_size}
                      name={"base_order_size"}
                      label={"Base order size (quantity)"}
                      handleChange={handleInput}
                      errorMsg={localState.baseOrderSizeError}
                      type="text"
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={data.balance_to_use}
                      name={"balance_to_use"}
                      label={"Balance to use"}
                      handleChange={handleInput}
                      handleBlur={handleBalanceToUseBlur}
                      errorMsg={localState.balanceToUseUnmatchError}
                      type="text"
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={data.trailling_deviation}
                      name={"trailling_deviation"}
                      label={"Trailling deviation"}
                      handleChange={handleInput}
                      type="number"
                    />
                  </Col>
                </>
              )}
            </Row>
            <Row>
              {data.trailling && (
                <>
                  <Col md="3">
                    <SettingsInput
                      value={data.stop_loss}
                      name={"stop_loss"}
                      label={"Stop loss"}
                      handleChange={handleInput}
                      type="number"
                      infoText="Should be kept as small as possible as this will increase funds needed to start base_order_size"
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={data.take_profit}
                      name={"take_profit"}
                      label={"Take profit"}
                      handleChange={handleInput}
                      type="number"
                    />
                  </Col>
                </>
              )}
            </Row>
            <br />
            <Row>
              <Col>
                <Button color="primary" onClick={saveSettings}>
                  Save
                </Button>{" "}
              </Col>
            </Row>
            <br />
          </Col>
        </Row>
      </Card.Body>
    </Card>
  )
}

export default AutotradePage
