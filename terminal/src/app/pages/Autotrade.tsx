import { type FC } from "react"
import { useAppDispatch } from "../hooks"
import { Button, Card, Col, Row, Form } from "react-bootstrap"
import { useEditSettingsMutation, useGetSettingsQuery } from "../../features/autotradeApiSlice"
import SettingsInput from "../components/SettingsInput"
import LightSwitch from "../components/LightSwitch"
import { useController, useForm } from "react-hook-form"
import { BotStrategy } from "../../utils/enums"

export const AutotradePage: FC<{}> = () => {

  const { data } = useGetSettingsQuery()
  const [ updateSettings, { isLoading: updatingSettings } ] = useEditSettingsMutation()
  const { control, handleSubmit } = useForm();

  const {
    field: candlestick_interval,
  } = useController({
    name: "candlestick_interval",
    rules: { required: true },
    defaultValue: data.candlestick_interval
  });

  const {
    field: max_active_autotrade_bots,
  } = useController({
    name: "max_active_autotrade_bots",
    rules: { required: true },
    defaultValue: data.max_active_autotrade_bots
  });

  const {
    field: telegram_signals,
  } = useController({
    name: "telegram_signals",
    rules: { required: true },
    defaultValue: data.telegram_signals
  });

  const {
    field: strategy,
  } = useController({
    name: "strategy",
    rules: { required: true },
    defaultValue: data.strategy
  });

  const {
    field: trailling,
  } = useController({
    name: "trailling",
    rules: { required: true },
    defaultValue: data.trailling
  });

  const {
    field: base_order_size,
  } = useController({
    name: "base_order_size",
    rules: { required: true },
    defaultValue: data.base_order_size
  });


  const {
    field: balance_to_use,
  } = useController({
    name: "balance_to_use",
    rules: { required: true },
    defaultValue: data.balance_to_use
  });

  const {
    field: trailling_deviation,
  } = useController({
    name: "trailling_deviation",
    rules: { required: true },
    defaultValue: data.trailling_deviation
  });

  const {
    field: stop_loss,
  } = useController({
    name: "stop_loss",
    rules: { required: true },
    defaultValue: data.stop_loss
  });

  const {
    field: take_profit,
  } = useController({
    name: "take_profit",
    rules: { required: true },
    defaultValue: data.take_profit
  });

  const saveSettings = (data) => {
    
    console.log(data)
    updateSettings(data)

  }


  return (
    <Card>
      <Card.Header>
        <Card.Title>Bot Autotrade settings</Card.Title>
      </Card.Header>
      <Card.Body>
        <Row>
          <Col md={"12"} sm="12">
            <Row>
              <Col md="3">
                <SettingsInput
                  value={candlestick_interval.value}
                  name={"candlestick_interval"}
                  label={"Candlestick interval"}
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
                  
                />
              </Col>
              <Col md="3">
                <label htmlFor="strategy">Strategy</label>
                <Form.Select
                  size="sm"
                  name="strategy"
                  value={data.strategy}
                >
                  <option value={BotStrategy.LONG}>Long</option>
                  <option value={BotStrategy.MARGIN_SHORT}>Margin short</option>
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

                />
              </Col>
              <Col md="3">
                <SettingsInput
                  value={max_active_autotrade_bots.value}
                  name={"max_active_autotrade_bots"}
                  label={"Max active autotrade bots"}
                  handleChange={max_active_autotrade_bots.onChange}
                />
              </Col>
            </Row>
            <Row>
              <Col md="3">
                <label htmlFor="trailling">Trailling</label>
                <br />
                <Button
                  name="trailling"
                  color={trailling.value ? "success" : "secondary"}
                  onClick={trailling.onChange}
                >
                  {trailling.value ? "On" : "Off"}
                </Button>
              </Col>
              {trailling.value && (
                <>
                  <Col md="3">
                    <SettingsInput
                      value={base_order_size.value}
                      name={"base_order_size"}
                      label={"Base order size (quantity)"}
                      type="text"
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={balance_to_use.value}
                      name={"balance_to_use"}
                      label={"Balance to use"}
                      type="text"
                      handleChange={balance_to_use.onChange}
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={trailling_deviation.value}
                      name={"trailling_deviation"}
                      label={"Trailling deviation"}
                      type="number"
                      handleChange={trailling_deviation.onChange}
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
                      value={stop_loss.value}
                      name={stop_loss.name}
                      label={"Stop loss"}
                      type="number"
                      infoText="Should be kept as small as possible as this will increase funds needed to start base_order_size"
                      handleChange={stop_loss.onChange}
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={take_profit.value}
                      name={"take_profit"}
                      label={"Take profit"}
                      type="number"
                      handleChange={take_profit.onChange}
                    />
                  </Col>
                </>
              )}
            </Row>
            <br />
            <Row>
              <Col>
                <Button color="primary" onClick={handleSubmit(saveSettings)}>
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
