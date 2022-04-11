import React, { useEffect } from "react";
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
import {
  getTestAutotradeSettings,
  saveTestAutoTradeSettings,
  setTestAutotradeSetting
} from "./actions";

export default function TestAutotrade() {
  const dispatch = useDispatch();
  const settingsProps = useSelector((state) => {
    return state.settingsReducer?.test_autotrade_settings;
  });
  const dispatchSetSettings = (payload) =>
    dispatch(setTestAutotradeSetting(payload));
  const saveSettings = () => dispatch(saveTestAutoTradeSettings(settingsProps));

  useEffect(() => {
    const getSettings = () => dispatch(getTestAutotradeSettings())
    getSettings();
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
    let traillingValue = "true"
    if (settingsProps.trailling === "true") {
      traillingValue = "false";
    }
    dispatchSetSettings({
      trailling: traillingValue,
    });
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
              {settingsProps && (
                <>
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={settingsProps.candlestick_interval}
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
                          settingsProps.trailling === "true"
                            ? "success"
                            : "secondary"
                        }
                        onClick={toggleTrailling}
                      >
                        {settingsProps.trailling === "true" ? "On" : "Off"}
                      </Button>
                    </Col>
                    <Col md="3">
                      <label htmlFor="test_autotrade">Autotrade?</label>
											<br />
                      <LightSwitch
                        value={settingsProps.test_autotrade}
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
                        value={settingsProps.telegram_signals}
                        name="telegram_signals"
                        toggle={toggle}
                      />
                    </Col>
                  </Row>
                  <Row>
                    {settingsProps.trailling === "true" && (
                      <Row>
                        <Col md="3">
                          <SettingsInput
                            value={settingsProps.take_profit}
                            name={"take_profit"}
                            label={"Take profit"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={settingsProps.trailling_deviation}
                            name={"trailling_deviation"}
                            label={"Trailling deviation"}
                            handleChange={handleInput}
                            type="number"
                          />
                        </Col>
                        <Col md="3">
                          <SettingsInput
                            value={settingsProps.stop_loss}
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
