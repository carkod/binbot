import React, { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Form,
  FormFeedback,
  FormGroup,
  Input,
  InputGroup,
  InputGroupText,
  Label,
  Row,
} from "reactstrap";
import { useImmer } from "use-immer";
import SettingsInput from "../../components/SettingsInput";
import SymbolSearch from "../../components/SymbolSearch";
import { checkValue } from "../../validations";

export const ControllerTab = ({
  blacklistData,
  symbols,
  settings,
  handleInput,
  saveSettings,
  handleBlacklist,
  toggleTrailling,
  toggleAutotrade,
  handleBalanceToUseBlur,
  balanceToUseUnmatchError,
  handleBalanceSizeToUseBlur,
  minBalanceSizeToUseError,
  triggerGbpHedge,
  allBalance,
  addAll,
}) => {
  const [addBlacklist, setAddBlacklist] = useImmer({ reason: "", pair: "" });
  const [removeBlacklist, setRemoveBlacklist] = useState("");
  const [error, setError] = useImmer(false);
  const [gbpHedge, setGbpHedge] = useState("");

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
      <Card>
        <CardHeader>
          <CardTitle>General settings for research signals</CardTitle>
        </CardHeader>
        <CardBody>
          <Row>
            <Col md={"12"} sm="12">
              <h2>Global settings</h2>
              {settings && (
                <>
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={settings.candlestick_interval}
                        name={"candlestick_interval"}
                        label={"Candlestick interval"}
                        handleChange={handleInput}
                      />
                    </Col>
                    <Col md="3">
                      <label>Autotrade?</label>
                      <br />
                      <Button
                        color={
                          settings.autotrade === 1 ? "success" : "secondary"
                        }
                        name="autotrade"
                        onClick={toggleAutotrade}
                      >
                        {settings.autotrade === 1 ? "On" : "Off"}
                      </Button>
                    </Col>
                    <Col md="3">
                      <SettingsInput
                        value={settings.max_request}
                        name={"max_request"}
                        label={"Max no. symbols streaming"}
                        handleChange={handleInput}
                        type="number"
                        min="1"
                      />
                    </Col>
                    <Col md="3">
                      <SettingsInput
                        value={settings.telegram_signals && 1}
                        name={"telegram_signals"}
                        label={"Send signals to telegram? 0 or 1"}
                        handleChange={handleInput}
                        type="number"
                        min="0"
                      />
                    </Col>
                  </Row>
                  {parseInt(settings.autotrade) === 1 && (
                    <>
                      <h4>Autotrade settings</h4>
                      <Row>
                        <Col md="3">
                          <SettingsInput
                            value={settings.balance_to_use}
                            name={"balance_to_use"}
                            label={"Balance to use"}
                            handleChange={handleInput}
                            handleBlur={handleBalanceToUseBlur}
                            errorMsg={balanceToUseUnmatchError}
                            type="text"
                          />
                        </Col>
                        <Col md="3">
                          <label htmlFor={"balance_size_to_use"}>
                            Base order for each bot
                          </label>
                          <InputGroup>
                            <Input
                              value={settings?.balance_size_to_use}
                              name={"balance_size_to_use"}
                              label={"Base order per bot"}
                              onChange={handleInput}
                              onBlur={handleBalanceSizeToUseBlur}
                              type="number"
                              min="0"
                            />
                            {settings.balance_to_use && (
                              <InputGroupText>
                                {settings.balance_to_use}
                              </InputGroupText>
                            )}
                            {minBalanceSizeToUseError && (
                              <FormFeedback>
                                {minBalanceSizeToUseError}
                              </FormFeedback>
                            )}
                          </InputGroup>
                          <Badge color="secondary" onClick={allBalance}>
                            Use 100%
                          </Badge>{" "}
                          <Badge color="secondary" onClick={addAll}>
                            Current balance
                          </Badge>
                        </Col>
                        <Col md="3" sm="6">
                          <label>Trailling</label>
                          <br />
                          <Button
                            color={
                              settings.trailling === "true"
                                ? "success"
                                : "secondary"
                            }
                            name="trailling"
                            onClick={toggleTrailling}
                          >
                            {settings.trailling === "true" ? "On" : "Off"}
                          </Button>
                        </Col>
                      </Row>
                      {settings.trailling === "true" && (
                        <Row>
                          <Col md="3">
                            <SettingsInput
                              value={settings.take_profit}
                              name={"take_profit"}
                              label={"Take profit"}
                              handleChange={handleInput}
                              type="number"
                            />
                          </Col>
                          <Col md="3">
                            <SettingsInput
                              value={settings.trailling_deviation}
                              name={"trailling_deviation"}
                              label={"Trailling deviation"}
                              handleChange={handleInput}
                              type="number"
                            />
                          </Col>
                          <Col md="3">
                            <SettingsInput
                              value={settings.stop_loss}
                              name={"stop_loss"}
                              label={"Stop loss"}
                              handleChange={handleInput}
                              type="number"
                            />
                          </Col>
                        </Row>
                      )}
                    </>
                  )}
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
              <Form inline>
                <h2>GBP hedging (panic sell)</h2>
                <FormGroup>
                  <Label for="gbpHedge">Asset e.g. BNB, BTC</Label>
                  <Input
                    value={gbpHedge}
                    name={"gbpHedge"}
                    onChange={(e) => setGbpHedge(e.target.value)}
                  />
                  <br />
                  <Button
                    color="primary"
                    onClick={() => triggerGbpHedge(gbpHedge)}
                  >
                    Buy BTC
                  </Button>
                </FormGroup>
              </Form>
              <hr />
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
            </Col>
          </Row>
        </CardBody>
      </Card>
    </>
  );
};

export default ControllerTab;
