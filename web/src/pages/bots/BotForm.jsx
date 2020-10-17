import React from "react";
import { connect } from "react-redux";
import { Button, Card, CardBody, CardFooter, CardHeader, CardTitle, Col, Container, Form, FormFeedback, Input, Label, Nav, NavItem, NavLink, Row, TabContent, TabPane, Badge } from "reactstrap";
import { getBalance }  from "../dashboard/actions";
import { getExchangeInfo } from "./actions";

class BotForm extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      _id: null,
      active: false,
      balance_available: "0",
      balance_usage: '1',
      balanceUsageError: false,
      balance_usage_size: '', // Computed
      base_order_size: '',
      cooldown: '0',
      deal_min_value: '0.001',
      max_so_count: '3',
      maxSOCountError: false,
      name: 'Default bot',
      nameError: false,
      pair: 'BTCUSDT',
      pairError: false,
      price_deviation_so: '0.0063',
      priceDevSoError: false,
      so_size: '0.0001',
      soSizeError: false,
      start_condition: true,
      strategy: 'long',
      take_profit: '0.003',
      takeProfitError: false,
      trailling: 'false',
      trailling_deviation: '0.0',
      formIsValid: false,
      activeTab: 'main'
    }
  }

  componentDidMount = () => {
    this.props.getBalance();
    this.props.getExchangeInfo();
  }

  checkValue = (value) => {
    if (value === '' || value === null || value === undefined) {
      return true;
    }
    return false;
  }

  checkMinValue = (value) => {
    /**
     * Check float value reaches minimum
     */
    const a = parseFloat(value)
    // Min required to operate
    const b = parseFloat("0.001")
    if (a > b) {
      return true;
    }
    return false;
  }

  requiredinValidation = () => {
    const { balance_usage, pair } = this.state;
    if (this.checkValue(balance_usage) && this.checkMinValue(balance_usage)) {
      this.setState({ balanceUsageError: true, formIsValid: false });
    } else {
      this.setState({ balanceUsageError: false });
    }

    if (this.checkValue(pair)) {
      this.setState({ pairError: true, formIsValid: false });
    } else {
      this.setState({ pairError: false });
    }

    this.setState({ formIsValid: true });
  }

  handleChange = (e) => {
    this.requiredinValidation();
    this.setState({ [e.target.name]: e.target.value });
  }

  handleSubmit = (e) => {
    e.preventDefault();
    this.requiredinValidation()
    if (this.state.formIsValid) {
      this.props.onSubmit(this.state);
    }
  }

  toggle = (tab) => {
    const { activeTab } = this.state;
    if (activeTab !== tab) this.setState({ activeTab: tab })
  }

  handleBaseOrder = () => {
    const balance = "0.003"
    this.setState({ base_order_size: balance })
  }

  render() {
    return (
      <div className="content">
        <Row>
          <Col md="12">
            <Card>
              <CardHeader>
                <CardTitle tag="h5">Users Behavior</CardTitle>
                <p className="card-category">24 Hours performance</p>
              </CardHeader>
              <CardBody>
                GRAPH GOES HERE
                {JSON.stringify(this.state)}
              </CardBody>
              <CardFooter>
                <hr />
                <div className="stats">
                  <i className="fa fa-history" /> Updated 3 minutes ago
              </div>
              </CardFooter>
            </Card>
          </Col>
        </Row>
        <Form onSubmit={this.handleSubmit}>
          <Row>

            <Col md="7" sm="12">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <Nav tabs>
                      <NavItem>
                        <NavLink
                          className={this.state.activeTab === "main" ? "active" : ""}
                          onClick={() => this.toggle("main")}
                        >
                          Main
                        </NavLink>
                      </NavItem>
                      <NavItem>
                        <NavLink
                          className={this.state.activeTab === "safety-orders" ? "active" : ""}
                          onClick={() => this.toggle('safety-orders')}
                        >
                          Safety Orders
                          </NavLink>
                      </NavItem>
                      <NavItem>
                        <NavLink
                          className={this.state.activeTab === "take-profit" ? "active" : ""}
                          onClick={() => this.toggle('take-profit')}
                        >
                          Take Profit
                          </NavLink>
                      </NavItem>
                    </Nav>
                  </CardTitle>
                </CardHeader>
                <CardBody>


                  {/*
                    Main tab
                  */}
                  <TabContent activeTab={this.state.activeTab}>
                    <TabPane tabId="main">
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label for="pair">Select Pair</Label>
                          <Input invalid={this.state.pairError} type="select" name="pair" id="pair" onChange={this.handleChange} value={this.state.pair}>
                            <option value="BTCUSDT">BTCUSDT</option>
                            <option value="STORJBUSD">STORJBUSD</option>
                            <option value="BNBBUSD">BNBBUSD</option>
                            <option value="BNBBUSD">BNBBUSD</option>
                          </Input>
                          <FormFeedback><strong>Pair</strong> is required.</FormFeedback>
                        </Col>
                        <Col md="6" sm="12">
                          <Label htmlFor="name">Name</Label>
                          <Input type="text" name="name" onChange={this.handleChange} value={this.state.name} />
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label htmlFor="strategy">Strategy</Label>
                          <Input type="select" name="strategy" onChange={this.handleChange} value={this.state.strategy}>
                            <option defaultChecked value="long">Long</option>
                            <option value="short">Short</option>
                          </Input>
                          <small>Long for trends. Short for vertical movement.</small>
                        </Col>
                        <Col md="6" sm="12">
                          <label htmlFor="base_order_size">Base order size</label>
                          <Input type="number" step="0.001" name="base_order_size" onChange={this.handleChange} value={this.state.base_order_size} />
                          <Badge color="secondary" onClick={this.handleBaseOrder}>All</Badge>
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <label htmlFor="deal_min_value">Deal minimum value</label>
                          <Input type="text" name="deal_min_value" onChange={this.handleChange} value={this.state.deal_min_value} />
                        </Col>
                        <Col md="6" sm="12">
                          <label htmlFor="cooldown">Cooldown</label>
                          <Input type="text" name="cooldown" onChange={this.handleChange} value={this.state.cooldown} />
                        </Col>
                      </Row>
                    </TabPane>


                    {/*
                      Safey orders tab
                    */}
                    <TabPane tabId="safety-orders">
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label htmlFor="strategy">Maximum number of Safety Orders</Label>
                          <Input invalid={this.state.maxSOCountError} type="text" name="max_so_count" onChange={this.handleChange} value={this.state.max_so_count} />
                          <FormFeedback><strong>Safety order size</strong> is required.</FormFeedback>
                          <small>If value = 0, Safety orders will be turned off</small>
                        </Col>
                        <Col md="6" sm="12">
                          <Label for="so_size">Safety order size</Label>
                          <Input invalid={this.state.soSizeError} type="number" name="so_size" id="so_size" onChange={this.handleChange} value={this.state.so_size} />
                          <FormFeedback><strong>Safety order size</strong> is required.</FormFeedback>
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="10" sm="12">
                          <Label htmlFor="price_deviation_so">Price deviation</Label>
                          <Input invalid={this.state.priceDevSoError} type="number" name="price_deviation_so" id="price_deviation_so" onChange={this.handleChange} value={this.state.price_deviation_so} />
                          <FormFeedback><strong>Price deviation</strong> is required.</FormFeedback>
                          <small>How much does the price have to drop to create a Safety Order?</small>
                        </Col>
                      </Row>
                    </TabPane>

                    {/*
                      Take profit tab
                    */}
                    <TabPane tabId="take-profit">
                      <Container>
                        <Row className="u-margin-bottom">
                          <Col md="8" sm="12">
                            <Label for="take_profit">Take profit at:</Label>
                            <Input invalid={this.state.takeProfitError} type="number" name="take_profit" id="take_profit" onChange={this.handleChange} value={this.state.take_profit} />
                            <FormFeedback><strong>Take profit</strong> is required.</FormFeedback>
                          </Col>
                        </Row>
                        <Row className="u-margin-bottom">
                          <Col md="6" sm="12">
                            <label>Trailling</label>
                            <Button color={this.state.trailling === "true" ? "success" : "secondary"} onClick={() =>
                              this.setState({ trailling: this.state.trailling === "true" ? "false" : "true" })}>
                              {this.state.trailling === "true" ? "On" : "Off"}
                            </Button>
                          </Col>
                          {this.state.trailling === "true" &&
                            <Col md="6" sm="12">
                              <Label htmlFor="trailling_deviation">Trailling deviation</Label>
                              <Input type="text" name="trailling_deviation" onChange={this.handleChange} value={this.state.trailling_deviation} />
                            </Col>
                          }
                        </Row>
                      </Container>
                    </TabPane>

                  </TabContent>


                  <Row>
                    <div className="update ml-auto mr-auto">
                      <Button
                        className="btn-round"
                        color="primary"
                        type="submit"
                      >Save</Button>
                    </div>
                  </Row>

                </CardBody>
              </Card>
            </Col>
            <Col md="5" sm="12">
              <Card>
                <CardHeader>
                  <CardTitle tag="h5">Balance Analysis</CardTitle>
                </CardHeader>
                <CardBody>
                  <Row className="u-margin-bottom">
                    <Col md="8" sm="12">
                      Balance usage ({100 * this.state.balance_usage}%)
                    </Col>
                    <Col md="4" sm="12">
                      {this.props.balances && this.props.balances.map((e, i) => 
                          <div key={i} className="u-primary-color"><strong>{`${e.free} ${e.asset}`}</strong></div>
                      )}
                    </Col>
                  </Row>
                  <Row>
                    <Col md="8" sm="12">
                      Balance available for Safety Orders
                    </Col>
                    <Col md="4" sm="12">
                      0.003 BNB
                    </Col>
                  </Row>
                </CardBody>
              </Card>
            </Col>

          </Row>
        </Form>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: balances } = state.balanceReducer;

  return {
    balances: balances,
  }
}

export default connect(mapStateToProps, { getBalance, getExchangeInfo })(BotForm);
