import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Row,
} from "reactstrap";
import LightSwitch from "../../components/LightSwitch";
import SettingsInput from "../../components/SettingsInput";
import { getBalanceRaw } from "../../state/balances/actions";
import {
  getTestAutotradeSettings,
  saveTestAutoTradeSettings,
  setTestAutotradeSetting,
} from "./actions";

export default function TestAutotrade() {
  const [localState, setLocalState] = useState({
    balanceToUseUnmatchError: ""
  });
  const dispatch = useDispatch();
  const settingsProps = useSelector((state) => {
    return {
      balance: state.balanceRawReducer?.data,
      testAutotradeSettings: state.settingsReducer?.test_autotrade_settings,
    };
  });
  const dispatchSetSettings = (payload) =>
    dispatch(setTestAutotradeSetting(payload));
  const saveSettings = () =>
    dispatch(saveTestAutoTradeSettings(settingsProps.testAutotradeSettings));

  useEffect(() => {
    const getSettings = () => dispatch(getTestAutotradeSettings());
    const getBalance = () => dispatch(getBalanceRaw());
    getSettings();
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
    if (settingsProps.testAutotradeSettings.trailling === "true") {
      traillingValue = "false";
    }
    dispatchSetSettings({
      trailling: traillingValue,
    });
  };

  const handleBalanceToUseBlur = () => {
    const searchBalance = settingsProps.balance.findIndex(
      (b) => b.asset === settingsProps.testAutotradeSettings.balance_to_use
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
          <CardTitle>Test bot Autotrade settings</CardTitle>
        </CardHeader>
        <CardBody>
          <Row>
            <Col md={"12"} sm="12">
              {settingsProps.testAutotradeSettings && (
                <>
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={
                          settingsProps.testAutotradeSettings
                            .candlestick_interval
                        }
                        name={"candlestick_interval"}
                        label={"Candlestick interval"}
                        handleChange={handleInput}
                      />
                    </Col>
                    <Col md="3">
                      <label htmlFor="trailling">Trailling</label>
                      <br />
                      <Button
                        name="trailling"
                        color={
                          settingsProps.testAutotradeSettings.trailling ===
                          "true"
                            ? "success"
                            : "secondary"
                        }
                        onClick={toggleTrailling}
                      >
                        {settingsProps.testAutotradeSettings.trailling ===
                        "true"
                          ? "On"
                          : "Off"}
                      </Button>
                    </Col>
                    <Col md="3">
                      <label htmlFor="test_autotrade">Autotrade?</label>
                      <br />
                      <LightSwitch
                        value={
                          settingsProps.testAutotradeSettings.test_autotrade
                        }
                        name="test_autotrade"
                        toggle={toggle}
                      />
                    </Col>
                    <Col md="3">
                      <label htmlFor="telegram_signals">
                        Send messages to telegram?
                      </label>
                      <br />
                      <LightSwitch
                        value={
                          settingsProps.testAutotradeSettings.telegram_signals
                        }
                        name="telegram_signals"
                        toggle={toggle}
                      />
                    </Col>
                  </Row>
                  <Row>
                    {settingsProps.testAutotradeSettings.trailling ===
                      "true" && (
                      <Row>
                        <Col md="3">
                          <SettingsInput
                            value={
                              settingsProps.testAutotradeSettings.balance_to_use
                            }
                            name={"balance_to_use"}
                            label={"Balance to use"}
                            handleChange={handleInput}
                            handleBlur={handleBalanceToUseBlur}
                            errorMsg={localState.balanceToUseUnmatchError}
                            type="text"
                          />
                          <SettingsInput
                            value={
                              settingsProps.testAutotradeSettings.take_profit
                            }
                            name={"take_profit"}
                            label={"Take profit"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={
                              settingsProps.testAutotradeSettings
                                .trailling_deviation
                            }
                            name={"trailling_deviation"}
                            label={"Trailling deviation"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={
                              settingsProps.testAutotradeSettings.stop_loss
                            }
                            name={"stop_loss"}
                            label={"Stop loss"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                      </Row>
                    )}
                  </Row>
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
