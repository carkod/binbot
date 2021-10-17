import React, { useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  FormGroup,
  Input,
  Label,
  Row
} from "reactstrap";
import { useImmer } from "use-immer";
import SymbolSearch from "../../components/SymbolSearch";
import { checkValue } from "../../validations";

const SettingsInput = ({ value, name, label, handleChange }) => {
  return (
    <FormGroup>
      <Label for={name}>{label}</Label>
      <Input
        type="input"
        name={name}
        id={name}
        onChange={handleChange}
        defaultValue={value}
      />
    </FormGroup>
  );
};

export const ControllerTab = ({
  blacklistData,
  symbols,
  settings,
  handleInput,
  saveSettings,
  handleBlacklist,
}) => {
  const [addBlacklist, setAddBlacklist] = useImmer({ reason: "", pair: "" });
  const [removeBlacklist, setRemoveBlacklist] = useState("");
  const [error, setError] = useImmer(false);

  const onAction = (action, state) => {
    // Validation
    if (
      (action === "add" && checkValue(addBlacklist.pair)) ||
      (action === "remove" && checkValue(removeBlacklist))
    ) {
      setError(true);
    } else {
      handleBlacklist(action, state);
    }
    setError(false);
  };

  return (
    <>
      <Row>
        <Col md="12" sm="3">
          <Card>
            <CardHeader>
              <CardTitle>General settings for research signals</CardTitle>
            </CardHeader>
            <CardBody>
              <h2>Global settings</h2>
              {settings && (
                <>
                  <Row>
                    <Col md="4">
                      <SettingsInput
                        value={settings.candlestick_interval}
                        name={"candlestick_interval"}
                        label={"Candlestick interval"}
                        handleChange={handleInput}
                      />
                    </Col>
                    <Col md="4">
                      <SettingsInput
                        value={settings.autotrade}
                        name={"autotrade"}
                        label={"Allow autotrade? 0 or 1"}
                        handleChange={handleInput}
                      />
                    </Col>
                  </Row>
                  {parseInt(settings.autotrade) === 1 &&
                  <>
                    <h4>Autotrade settings</h4>
                    <Row>
                      <Col md="3">
                        <SettingsInput
                          value={settings.balance_to_use}
                          name={"balance_to_use"}
                          label={"Balanace to use"}
                          handleChange={handleInput}
                        />
                      </Col>
                      <Col md="3">
                        <SettingsInput
                          value={settings.take_profit}
                          name={"take_profit"}
                          label={"Take profit"}
                          handleChange={handleInput}
                        />
                      </Col>
                      <Col md="3">
                        <SettingsInput
                          value={settings.trailling_deviation}
                          name={"trailling_deviation"}
                          label={"Trailling deviation"}
                          handleChange={handleInput}
                        />
                      </Col>
                      <Col md="3">
                        <SettingsInput
                          value={settings.stop_loss}
                          name={"stop_loss"}
                          label={"Stop loss"}
                          handleChange={handleInput}
                        />
                      </Col>
                    </Row>
                  </>
                  }
                  <Row>
                    <Col>
                      <Button color="primary" onClick={saveSettings}>
                        Save global settings
                      </Button>{" "}
                    </Col>
                  </Row>
                  <br />
                  <hr />
                </>
              )}
              <>
              <h2>Blacklist</h2>
                <Row>
                  {blacklistData && blacklistData.length > 0 && (
                    <Col md="6">
                      <FormGroup>
                        <Label for="blacklist">View blacklisted</Label>
                        <Input
                          type="select"
                          name="blacklist"
                          id="blacklisted"
                          defaultValue={""}
                          onChange={(e) =>
                            setRemoveBlacklist(
                              (draft) => (draft = e.target.value)
                            )
                          }
                        >
                          <option value={""}> </option>
                          {blacklistData.map((x, i) => (
                            <option key={i} value={x._id}>
                              {x._id} ({x.reason})
                            </option>
                          ))}
                        </Input>
                      </FormGroup>
                      <Button
                        color="primary"
                        onClick={() => onAction("delete", removeBlacklist)}
                      >
                        Delete
                      </Button>
                    </Col>
                  )}
                  <Col md="3">
                    <FormGroup>
                      <SymbolSearch
                        name="pair"
                        label="Add new blacklisted coin"
                        options={symbols}
                        selected={addBlacklist.pair}
                        handleChange={(value) =>
                          setAddBlacklist((draft) => {
                            draft.pair = value[0];
                          })
                        }
                      />
                    </FormGroup>
                  </Col>
                  <Col md="3">
                    <FormGroup>
                      <Label for="reason">Reason</Label>
                      <Input
                        type="text"
                        name="reason"
                        id="reason"
                        value={addBlacklist.reason}
                        onChange={(e) =>
                          setAddBlacklist((draft) => {
                            draft.reason = e.target.value;
                          })
                        }
                      />
                    </FormGroup>
                    <Button
                      color="primary"
                      onClick={() => onAction("add", addBlacklist)}
                    >
                      Add
                    </Button>{" "}
                  </Col>
                </Row>
                {error && <Alert color="danger">Missing required field</Alert>}
              </>
            </CardBody>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default ControllerTab;
