import React, { useState } from "react";
import {
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

export const ControllerTab = ({
  blacklistData,
  symbols,
  addToBlacklist,
  removeFromBlacklist,
  triggerGbpHedge,
}) => {
  const [addBlacklist, setAddBlacklist] = useImmer({ reason: "", pair: "" });
  const [removeBlacklist, setRemoveBlacklist] = useState("");
  const [gbpHedge, setGbpHedge] = useState("");

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
                          onChange={(e) => setRemoveBlacklist(e.target.value)}
                        >
                          <option value={""}> </option>
                          {blacklistData.map((x, i) => (
                            <option key={i} value={x._id}>
                              {x.pair} ({x.reason})
                            </option>
                          ))}
                        </Input>
                      </FormGroup>
                      <Button
                        color="primary"
                        onClick={() => removeFromBlacklist(removeBlacklist)}
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
                      onClick={() => addToBlacklist(addBlacklist)}
                    >
                      Add
                    </Button>{" "}
                  </Col>
                </Row>
              </>
            </Col>
          </Row>
        </CardBody>
      </Card>
    </>
  );
};

export default ControllerTab;
