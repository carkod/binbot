import { type FC, useEffect, useState } from "react";
import { useGetRawBalanceQuery } from "../../features/balanceApiSlice";
import { Button, Card, Col, Row, Form } from "react-bootstrap";
import SymbolSearch from "../components/SymbolSearch";
import { useGetSymbolsQuery } from "../../features/symbolApiSlice";
import {
  type BlacklistItem,
  useAddBlacklistItemMutation,
  useDeleteBlacklistItemMutation,
  useGetBlacklistQuery,
} from "../../features/blacklistApiSlice";

const BlacklistPage: FC = () => {
  const { data: symbols } = useGetSymbolsQuery();
  const { data: blacklistData } = useGetBlacklistQuery();
  const [addBlacklistItem] = useAddBlacklistItemMutation();
  const [deleteBlacklistItem] = useDeleteBlacklistItemMutation();
  const [order, setOrder] = useState<boolean>(false); // true = desc = -1, false = asc = 1
  const [symbolsList, setSymbolsList] = useState<string[]>([]);

  const [seletedBlacklistItem, setSeletedBlacklistItem] =
    useState<BlacklistItem>({
      pair: "",
      reason: "",
    });
  const [sideFilter, setSideFilter] = useState<string>("ALL");

  const { data: balances } = useGetRawBalanceQuery();

  const handlePairBlur = (e) => {
    const pair = e.target.value;
  };

  useEffect(() => {
    if (symbols) {
      setSymbolsList(symbols);
    }
    if (balances) {
      console.log(balances);
    }
    if (blacklistData) {
      console.log(blacklistData);
    }
  }, [symbols, balances, symbolsList, blacklistData]);

  return (
    <div className="content">
      <Card>
        <Card.Header>
          <Card.Title>Blacklist</Card.Title>
        </Card.Header>
        <Card.Body>
          <Row>
            {blacklistData && blacklistData.length > 0 && (
              <Col md="6">
                <Form.Group>
                  <Form.Label htmlFor="blacklist">View blacklisted</Form.Label>
                  <Form.Control
                    type="select"
                    name="blacklist"
                    id="blacklisted"
                    value={seletedBlacklistItem.pair}
                    onChange={(e) =>
                      setSeletedBlacklistItem({
                        ...seletedBlacklistItem,
                        pair: e.target.value,
                      })
                    }
                  >
                    <option value={""}> </option>
                    {blacklistData.map((x, i) => (
                      <option key={i} value={x.pair}>
                        {x.pair} ({x.reason})
                      </option>
                    ))}
                  </Form.Control>
                </Form.Group>
                <Button
                  color="primary"
                  onClick={() => {
                    deleteBlacklistItem(seletedBlacklistItem.pair);
                  }}
                >
                  Delete
                </Button>
              </Col>
            )}
            <Col md="3">
              <Form.Group>
                <SymbolSearch
                  name="pair"
                  label="Select pair"
                  options={symbolsList}
                  value={""}
                  onBlur={handlePairBlur}
                  required
                />
              </Form.Group>
            </Col>
            <Col md="3">
              <Form.Group>
                <Form.Label htmlFor="reason">Reason</Form.Label>
                <Form.Control
                  type="text"
                  name="reason"
                  id="reason"
                  value={seletedBlacklistItem.reason}
                  onChange={(e) =>
                    setSeletedBlacklistItem({
                      ...seletedBlacklistItem,
                      reason: e.target.value,
                    })
                  }
                />
              </Form.Group>
              <Button
                color="primary"
                onClick={() => addBlacklistItem(seletedBlacklistItem)}
              >
                Add
              </Button>{" "}
            </Col>
          </Row>
          {/* <Row>
            <Col md={"12"} sm="12">
                <h3>Blacklist</h3>
                
                <br />
                <h3>Subscribed</h3>
                <Row>
                  {subscribedSymbols && subscribedSymbols.length > 0 && (
                    <Col md="6">
                      <Form.Group>
                        <Label htmlFor="subscribed">Following list of cryptos are listened on by websockets</Label>
                        <Input
                          type="select"
                          name="subscribed"
                          id="blacklisted"
                        >
                          <option value={""}> </option>
                          {subscribedSymbols.map((x, i) => (
                            <option key={i} value={x._id}>
                              {x.pair} ({x.reason})
                            </option>
                          ))}
                        </Input>
                      </Form.Group>
                    </Col>
                  )}
                </Row>
              </>
            </Col>
          </Row> */}
        </Card.Body>
      </Card>
    </div>
  );
};

export default BlacklistPage;
