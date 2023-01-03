import React, { useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Form,
  FormGroup,
  Input,
  Label,
  Row,
} from "reactstrap";
import { useImmer } from "use-immer";
import SymbolSearch from "../../components/SymbolSearch";
import { checkValue } from "../../validations";

export const ControllerTab = ({
  blacklistData,
  symbols,
  handleBlacklist,
  triggerGbpHedge,
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
              <Form>
                <h3>GBP hedging (panic sell)</h3>
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
                <h3>Blacklist</h3>
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
                            <option key={i} value={x.id}>
                              {x.id} ({x.reason})
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
