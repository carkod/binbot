import React from "react";
import { connect } from "react-redux";
import { Badge, Button, Card, CardBody, CardFooter, CardHeader, CardTitle, Col, Container, Form, FormFeedback, Input, Label, Nav, NavItem, NavLink, Row, TabContent, TabPane } from "reactstrap";
import { getBalance } from "../dashboard/actions";
import { getSymbols, getSymbolInfo } from "./actions";
import { checkBalance, checkMinValue, checkValue, getCurrentPairBalance, percentageToFloat, toPercentage } from "./validations.js";

class BotForm extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      _id: null,
      active: false,
      balance_available: "0",
      balance_available_asset: "",
      balanceAvailableError: false,
      balance_usage: '1',
      balanceUsageError: false,
      balance_usage_size: '', // Computed
      base_order_size: '',
      baseOrderSizeError: false,
      cooldown: '0',
      deal_min_value: '0.001',
      max_so_count: '3',
      maxSOCountError: false,
      name: 'Default bot',
      nameError: false,
      pair: '',
      price_deviation_so: '0.63',
      priceDevSoError: false,
      so_size: '0',
      soSizeError: false,
      start_condition: true,
      strategy: 'long',
      take_profit: '3',
      takeProfitError: false,
      trailling: 'false',
      trailling_deviation: '0.63',
      formIsValid: false,
      activeTab: 'main'
    }
  }

  componentDidMount = () => {
    this.props.getBalance();
    this.props.getSymbols();
  }

  componentDidUpdate = (p, s) => {
    if (p.symbolInfo !== this.props.symbolInfo) {
      this.computeAvailableBalance();
    }
    if (s.strategy !== this.state.strategy) {
      this.computeAvailableBalance();
    }
  }

  requiredinValidation = () => {
    const { balance_usage, pair, take_profit, base_order_size } = this.state;
    if (checkValue(balance_usage) && checkMinValue(balance_usage)) {
      this.setState({ balanceUsageError: true, formIsValid: false });
    } else {
      this.setState({ balanceUsageError: false });
    }

    if (checkValue(pair)) {
      this.setState({ pairError: true, formIsValid: false });
    } else {
      this.setState({ pairError: false });
    }

    if (checkValue(base_order_size)) {
      this.setState({ baseOrderSizeError: true, formIsValid: false });
    } else {
      this.setState({ baseOrderSizeError: false });
    }

    if (checkValue(take_profit)) {
      this.setState({ takeProfitError: true, formIsValid: false });
    } else {
      this.setState({ takeProfitError: false });
    }

    this.setState({ formIsValid: true });
  }

  handleChange = (e) => {
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

  computeAvailableBalance = () => {
    /**
     * Refer to bots.md
     */
    const { strategy, base_order_size, so_size, max_so_count } = this.state;
    const { balances } = this.props;
    let asset;
    if (strategy === "long") {
      asset = this.props.symbolInfo.baseAsset;
    } else {
      asset = this.props.symbolInfo.quoteAsset;
    }

    let value = "0";
    let name = "";
    balances.forEach(x => {
      if (asset === x.asset) {
        value = x.free
        name = x.asset
      }
    });

    if (!checkValue(value) && !checkBalance(value)) {
      const updatedValue = value - ((base_order_size * 1) + (so_size * max_so_count))

      // Check that we have enough funds
      // If not return error
      if (parseFloat(updatedValue) >= 0) {
        this.setState({ balance_available: updatedValue, balance_available_asset: name, baseOrderSizeError: false, balanceAvailableError: false });
      } else {
        this.setState({ baseOrderSizeError: true, formIsValid: false })
      }
    } else {
      this.setState({ balance_available: value, balance_available_asset: name, balanceAvailableError: true, formIsValid: false })
    }
  }

  handlePairChange = (e) => {
    // Get pair base or quote asset and set new pair
    this.props.getSymbolInfo(e.target.value);
    this.setState({ [e.target.name]: e.target.value });
  }

  handleStrategy = (e) => {
    // Get pair base or quote asset and set new strategy
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.setState({ [e.target.name]: e.target.value });
  }

  handleBaseChange = (e) => {
    const { balance_available_asset } = this.state;
    const qty = getCurrentPairBalance(this.props.balances, balance_available_asset);
    if (!checkValue(qty) && !checkBalance(qty)) {
      const updatedValue = qty - (e.target.value * 1)

      // Check that we have enough funds
      // If not return error
      if (parseFloat(updatedValue) >= 0) {
        this.setState({ [e.target.name]: e.target.value, balance_available: updatedValue, baseOrderSizeError: false })
      } else {
        this.setState({ [e.target.name]: e.target.value, baseOrderSizeError: true, formIsValid: false })
      }

    }
  }

  addAll = () => {
    const { pair, balance_available } = this.state;
    if (!checkValue(pair)) {
      this.props.getSymbolInfo(pair);
      this.setState({ base_order_size: balance_available });
    } else {
      this.setState({ balanceAvailableError: true, formIsValid: false })
    }
  }

  handleSafety = (e) => {
    const { pair } = this.state;
    this.setState({ [e.target.name]: e.target.value })
    this.props.getSymbolInfo(pair);
  }

  handlePercentageChanges = (e) => {
    const value = percentageToFloat(e.target.value);
    this.setState({ [e.target.name]: e.target.value });
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
                          <Label for="pair">Pair<span className="u-required">*</span></Label>
                          <Input invalid={this.state.balanceAvailableError} type="select" name="pair" id="pair" onChange={this.handlePairChange} onBlur={this.handlePairBlur} value={this.state.pair}>
                            <option value="" defaultChecked>Select pair</option>
                            {this.props.symbols && this.props.symbols.map((x, i) => (
                              <option key={i} value={x}>{x}</option>
                            ))}

                          </Input>
                          <FormFeedback valid={!this.state.balanceAvailableError}><strong>Balance</strong> is not available for this pair.</FormFeedback>
                        </Col>
                        <Col md="6" sm="12">
                          <Label htmlFor="name">Name</Label>
                          <Input type="text" name="name" onChange={this.handleChange} value={this.state.name} />
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label htmlFor="strategy">Strategy<span className="u-required">*</span></Label>
                          <Input type="select" name="strategy" onChange={this.handleStrategy} value={this.state.strategy}>
                            <option defaultChecked value="long">Long</option>
                            <option value="short">Short</option>
                          </Input>
                          <small>Long for trends. Short for vertical movement.</small>
                        </Col>
                        <Col md="6" sm="12">
                          <label htmlFor="base_order_size">Base order size<span className="u-required">*</span></label>
                          <Input invalid={this.state.baseOrderSizeError} type="text" name="base_order_size" onChange={this.handleBaseChange} value={this.state.base_order_size} />
                          <FormFeedback valid={!this.state.baseOrderSizeError} >Not enough balance</FormFeedback>
                          <Badge color="secondary" onClick={this.addAll}>All</Badge>
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
                        {parseInt(this.state.max_so_count) > 0 &&
                          <Col md="6" sm="12">
                            <Label for="so_size">Safety order size</Label>
                            <Input invalid={this.state.soSizeError} type="text" name="so_size" id="so_size" onChange={this.handleSafety} value={this.state.so_size} />
                            <FormFeedback><strong>Safety order size</strong> is required.</FormFeedback>
                          </Col>
                        }
                      </Row>
                      <Row className="u-margin-bottom">
                        {parseInt(this.state.max_so_count) > 0 &&
                          <Col md="10" sm="12">
                            <Label htmlFor="price_deviation_so">Price deviation (%)</Label>
                            <Input invalid={this.state.priceDevSoError} type="text" name="price_deviation_so" id="price_deviation_so" onChange={this.handlePercentageChanges} value={this.state.price_deviation_so} />
                            <FormFeedback><strong>Price deviation</strong> is required.</FormFeedback>
                            <small>How much does the price have to drop to create a Safety Order?</small>
                          </Col>
                        }
                      </Row>
                    </TabPane>

                    {/*
                      Take profit tab
                    */}
                    <TabPane tabId="take-profit">
                      <Container>
                        <Row className="u-margin-bottom">
                          <Col md="8" sm="12">
                            <Label for="take_profit">Take profit at (%): <span className="u-required">*</span></Label>
                            <Input invalid={this.state.takeProfitError} type="text" name="take_profit" id="take_profit" onChange={this.handlePercentageChanges} value={this.state.take_profit} />
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
                              <Label htmlFor="trailling_deviation">Trailling deviation (%)</Label>
                              <Input type="text" name="trailling_deviation" onChange={this.handlePercentageChanges} value={this.state.trailling_deviation} />
                            </Col>
                          }
                        </Row>
                      </Container>
                    </TabPane>

                  </TabContent>
                  <Row>
                    <div className="update ml-auto mr-auto">
                      <Button className="btn-round" color="primary" type="submit" >Save</Button>
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
                      <div className="u-primary-color"><strong>{`${this.state.balance_available} ${this.state.balance_available_asset}`}</strong></div>
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
  const { data: symbols } = state.botReducer;
  const { data: symbolInfo } = state.symbolInfoReducer;

  return {
    balances: balances,
    symbols: symbols,
    symbolInfo: symbolInfo
  }
}

export default connect(mapStateToProps, { getBalance, getSymbols, getSymbolInfo })(BotForm);
