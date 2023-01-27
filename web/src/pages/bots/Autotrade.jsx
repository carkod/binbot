import React, { useEffect, useState } from "react";
import Form from "react-bootstrap/Form";
import { useDispatch, useSelector } from "react-redux";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Row
} from "reactstrap";
import LightSwitch from "../../components/LightSwitch";
import SettingsInput from "../../components/SettingsInput";
import { getBalanceRaw } from "../../state/balances/actions";
import { editSettings, getSettings, setSettingsState } from "./actions";

export default function Autotrade() {
  const [localState, setLocalState] = useState({
    balanceToUseUnmatchError: "",
  });
  const dispatch = useDispatch();
  const settingsProps = useSelector((state) => {
    return {
      balance: state.balanceRawReducer?.data,
      autotradeSettings: state.settingsReducer?.settings,
    };
  });
  const dispatchSetSettings = (payload) => dispatch(setSettingsState(payload));
  const saveSettings = () => {
    dispatch(editSettings(settingsProps.autotradeSettings));
  };

  useEffect(() => {
    const retrieveSettings = () => dispatch(getSettings());
    const getBalance = () => dispatch(getBalanceRaw());
    retrieveSettings();
    getBalance();
  }, [dispatch]);

  const handleInput = (e) =>
    dispatchSetSettings({
      [e.target.name]: e.target.value,
    });

  const toggle = (name, value) => {
    if (parseInt(value) === 0) {
      value = 1;
    } else {
      value = 0;
    }
    dispatchSetSettings({
      [name]: value,
    });
  };

  const toggleTrailling = () => {
    let traillingValue = "true";
    if (settingsProps.autotradeSettings.trailling === "true") {
      traillingValue = "false";
    }
    dispatchSetSettings({
      trailling: traillingValue,
    });
  };

  const handleBalanceToUseBlur = () => {
    const searchBalance = settingsProps.balance.findIndex(
      (b) => b.asset === settingsProps.autotradeSettings.balance_to_use
    );
    if (searchBalance === -1) {
      setLocalState({
        balanceToUseUnmatchError:
          "Balance to use does not match available balance. Autotrade will fail.",
      });
    } else {
      setLocalState({
        balanceToUseUnmatchError: "",
      });
    }
  };

  return (
    <div className="content">
      <Card>
        <CardHeader>
          <CardTitle>Bot Autotrade settings</CardTitle>
        </CardHeader>
        <CardBody>
          <Row>
            <Col md={"12"} sm="12">
              {settingsProps.autotradeSettings && (
                <>
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={
                          settingsProps.autotradeSettings.candlestick_interval
                        }
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
                        value={settingsProps.autotradeSettings.telegram_signals}
                        name="telegram_signals"
                        toggle={toggle}
                      />
                    </Col>
                    <Col md="3">
                      <label htmlFor="strategy">Strategy</label>
                      <Form.Select
                        size="sm"
                        name="strategy"
                        onClick={handleInput}
                        value={settingsProps.autotradeSettings.strategy}
                      >
                        <option value="long">Long</option>
                        <option value="short">Short</option>
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
                        value={settingsProps.autotradeSettings.autotrade}
                        name="autotrade"
                        toggle={toggle}
                      />
                    </Col>
                    <Col md="3">
                      <SettingsInput
                        value={
                          settingsProps.autotradeSettings
                            .max_active_autotrade_bots
                        }
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
                        color={
                          settingsProps.autotradeSettings.trailling === "true"
                            ? "success"
                            : "secondary"
                        }
                        onClick={toggleTrailling}
                      >
                        {settingsProps.autotradeSettings.trailling === "true"
                          ? "On"
                          : "Off"}
                      </Button>
                    </Col>
                    {settingsProps.autotradeSettings.trailling === "true" && (
                      <>
                        <Col md="3">
                          <SettingsInput
                            value={
                              settingsProps.autotradeSettings.base_order_size
                            }
                            name={"base_order_size"}
                            label={"Base order size (quantity)"}
                            handleChange={handleInput}
                            errorMsg={localState.baseOrderSizeError}
                            type="text"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={
                              settingsProps.autotradeSettings.balance_to_use
                            }
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
                            value={
                              settingsProps.autotradeSettings
                                .trailling_deviation
                            }
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
                    {settingsProps.autotradeSettings.trailling === "true" && (
                      <>
                        <Col md="3">
                          <SettingsInput
                            value={settingsProps.autotradeSettings.stop_loss}
                            name={"stop_loss"}
                            label={"Stop loss"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={settingsProps.autotradeSettings.take_profit}
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
                </>
              )}
            </Col>
          </Row>
        </CardBody>
      </Card>
    </div>
  );
}
