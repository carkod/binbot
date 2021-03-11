import React from "react";
import { connect } from "react-redux";
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
  Input,
  Label,
  Nav,
  NavItem,
  NavLink,
  Row,
  TabContent,
  TabPane,
  ButtonToggle,
} from "reactstrap";
import BalanceAnalysis from "../../components/BalanceAnalysis";
import Candlestick from "../../components/Candlestick";
import SymbolSearch from "../../components/SymbolSearch";
import {
  checkBalance,
  checkMinValue,
  checkValue,
  getCurrentPairBalance,
  intervalOptions,
} from "../../validations.js";
import { getBalance } from "../dashboard/actions";
import {
  createBot,
  editBot,
  getBot,
  activateBot,
  deactivateBot,
  getSymbolInfo,
  getSymbols,
  loadCandlestick,
} from "./actions";

class BotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      _id: props.match.params.id ? props.match.params.id : null,
      active: false,
      balance_available: "0",
      balance_available_asset: "",
      balanceAvailableError: false,
      balance_usage: "1",
      balanceUsageError: false,
      balance_usage_size: "0", // Computed
      base_order_size: "",
      baseOrderSizeError: false,
      cooldown: "0",
      deal_min_value: "0.001",
      max_so_count: "0",
      maxSOCountError: false,
      name: "Default bot",
      nameError: false,
      pair: "",
      price_deviation_so: "0.63",
      priceDevSoError: false,
      so_size: "0",
      soSizeError: false,
      start_condition: true,
      strategy: "long",
      take_profit: "3",
      takeProfitError: false,
      trailling: "false",
      trailling_deviation: "0.63",
      traillingDeviationError: false,
      auto_strategy: "true",
      formIsValid: true,
      activeTab: "main",
      candlestick_interval: intervalOptions[5],
    };
  }

  componentDidMount = () => {
    this.props.getBalance();
    this.props.getSymbols();
    if (this.props.match.params.id !== undefined) {
      this.props.getBot(this.props.match.params.id);
    }
  };

  componentDidUpdate = (p, s) => {
    if (p.symbolInfo !== this.props.symbolInfo) {
      this.computeAvailableBalance();
    }
    if (s.strategy !== this.state.strategy) {
      this.computeAvailableBalance();
    }
    if (p.bot !== this.props.bot) {
      this.setState({
        active: this.props.bot.active,
        balance_usage: this.props.bot.balance_usage,
        balance_usage_size: this.props.bot.balance_usage_size,
        base_order_size: this.props.bot.base_order_size,
        deal_min_value: this.props.bot.deal_min_value,
        max_so_count: this.props.bot.max_so_count,
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        price_deviation_so: this.props.bot.price_deviation_so,
        so_size: this.props.bot.so_size,
        start_condition: this.props.bot.start_condition,
        strategy: this.props.bot.strategy,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
      });
    }
    // If there is a newBotId, it means form was created
    // To make sure of this, check also URL has NO id param
    if (!checkValue(this.props.newBotId) && this.props.newBotId !== p.newBotId && checkValue(this.props.match.params.id)) {
      this.props.activateBot(this.props.newBotId);
      this.props.history.push(`/admin/bots-edit/${this.props.newBotId}`);
    }
  };

  requiredinValidation = () => {
    const {
      balance_usage,
      pair,
      take_profit,
      base_order_size,
      max_so_count,
      so_size,
      trailling,
      trailling_deviation,
    } = this.state;

    // If everything below is ok, form will be valid
    this.setState({ formIsValid: true });

    if (checkValue(balance_usage) && checkMinValue(balance_usage)) {
      this.setState({ balanceUsageError: true, formIsValid: false });
      return false;
    } else {
      this.setState({ balanceUsageError: false });
    }

    if (checkValue(pair)) {
      this.setState({ pairError: true, formIsValid: false });
      return false;
    } else {
      this.setState({ pairError: false });
    }

    if (checkValue(base_order_size) && checkBalance(base_order_size)) {
      this.setState({ baseOrderSizeError: true, formIsValid: false });
      return false;
    } else {
      this.setState({ baseOrderSizeError: false });
    }

    if (checkValue(take_profit) && checkBalance(take_profit)) {
      this.setState({ takeProfitError: true, formIsValid: false });
      return false;
    } else {
      this.setState({ takeProfitError: false });
    }

    if (checkValue(max_so_count)) {
      if (checkBalance(so_size) && checkBalance(so_size)) {
        this.setState({ soSizeError: true, formIsValid: false });
        return false;
      } else {
        this.setState({ soSizeError: false });
      }
    }

    if (trailling === "true") {
      if (
        checkBalance(trailling_deviation) &&
        checkBalance(trailling_deviation)
      ) {
        this.setState({ traillingDeviationError: true, formIsValid: false });
        return false;
      } else {
        this.setState({ traillingDeviationError: false });
      }
    }
    return true;
  };

  handleSubmit = async (e) => {
    e.preventDefault();
    const validation = this.requiredinValidation();
    if (validation) {
      const form = {
        active: String(this.state.active),
        balance_available: this.state.balance_available,
        balance_usage: this.state.balance_usage,
        base_order_size: String(this.state.base_order_size),
        cooldown: this.state.cooldown,
        deal_min_value: this.state.deal_min_value,
        max_so_count: this.state.max_so_count,
        name: this.state.name,
        pair: this.state.pair,
        price_deviation_so: this.state.price_deviation_so,
        so_size: this.state.so_size,
        start_condition: this.state.start_condition,
        strategy: this.state.strategy,
        take_profit: this.state.take_profit,
        trailling: this.state.trailling,
        trailling_deviation: this.state.trailling_deviation,
      };
      if (this.state._id === null) {
        this.props.createBot(form);
      } else {
        this.props.editBot(this.state._id, form);
        if (this.state.active === "false") {
          this.props.activateBot(this.state._id);
        }
      }
    }
  };

  toggle = (tab) => {
    const { activeTab } = this.state;
    if (activeTab !== tab) this.setState({ activeTab: tab });
  };

  computeAvailableBalance = () => {
    /**
     * Refer to bots.md
     */
    const { strategy, base_order_size, so_size, max_so_count } = this.state;
    const { balances, symbolInfo } = this.props;
    let asset;
    if (symbolInfo) {
      if (strategy === "long") {
        asset = symbolInfo.quoteAsset;
      } else {
        asset = symbolInfo.baseAsset;
      }

      let value = "0";
      let name = "";
      balances.forEach((x) => {
        if (asset === x.asset) {
          value = x.free;
          name = x.asset;
        }
      });

      if (!checkValue(value) && !checkBalance(value)) {
        const updatedValue =
          value - (base_order_size * 1 + so_size * max_so_count);

        // Check that we have enough funds
        // If not return error
        if (parseFloat(updatedValue) >= 0) {
          this.setState({
            balance_available: updatedValue,
            balance_available_asset: name,
            baseOrderSizeError: false,
            balanceAvailableError: false,
          });
        } else {
          this.setState({ baseOrderSizeError: true, formIsValid: false });
        }
      } else {
        this.setState({
          balance_available: value,
          balance_available_asset: name,
          balanceAvailableError: true,
          formIsValid: false,
        });
      }
    }
  };

  handlePairChange = (value) => {
    // Get pair base or quote asset and set new pair
    this.props.getSymbolInfo(value[0]);
    this.setState({ pair: value[0] });
  };

  handleStrategy = (e) => {
    // Get pair base or quote asset and set new strategy
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.setState({ [e.target.name]: e.target.value });
  };

  handleBaseChange = (e) => {
    const { balance_available_asset } = this.state;
    const qty = getCurrentPairBalance(
      this.props.balances,
      balance_available_asset
    );
    const updatedValue = qty - e.target.value * 1;

    // Check that we have enough funds
    // If not return error
    if (parseFloat(updatedValue) >= 0) {
      this.setState({
        [e.target.name]: e.target.value,
        balance_available: updatedValue,
        baseOrderSizeError: false,
      });
    } else {
      this.setState({
        [e.target.name]: e.target.value,
        baseOrderSizeError: true,
        formIsValid: false,
      });
    }
  };

  addAll = () => {
    const { pair, balance_available } = this.state;
    if (!checkValue(pair)) {
      this.props.getSymbolInfo(pair);
      this.setState({ base_order_size: balance_available });
    } else {
      this.setState({ balanceAvailableError: true, formIsValid: false });
    }
  };

  handleSafety = (e) => {
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.setState({ [e.target.name]: e.target.value });
  };

  handleChange = (e) => {
    e.preventDefault();
    setTimeout(this.setState({ [e.target.name]: e.target.value }), 3000);
  };

  handleBlur = () => {
    this.props.loadCandlestick(this.state.pair,this.state.candlestick_interval);
    this.computeAvailableBalance();
  };

  render() {
    return (
      <div className="content">
        <Row>
          <Col md="12">
            <Card style={{ minHeight: "650px" }}>
              <CardHeader>
                <CardTitle tag="h5">{this.state.pair}</CardTitle>
                {intervalOptions.map((item) => (
                  <Badge
                    key={item}
                    onClick={() => this.setState({ candlestick_interval: item })}
                    color={this.state.candlestick_interval === item ? "primary" : "secondary"}
                    className="btn"
                  >
                    {item}
                  </Badge>
                ))}
              </CardHeader>
              <CardBody>
                {this.props.candlestick && this.state.pair !== "" ? (
                  <Candlestick
                    data={this.props.candlestick}
                    bot={this.state}
                  />
                ) : (
                  ""
                )}
              </CardBody>
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
                          className={
                            this.state.activeTab === "main" ? "active" : ""
                          }
                          onClick={() => this.toggle("main")}
                        >
                          Main
                        </NavLink>
                      </NavItem>
                      <NavItem>
                        <NavLink
                          className={
                            this.state.activeTab === "safety-orders"
                              ? "active"
                              : ""
                          }
                          onClick={() => this.toggle("safety-orders")}
                        >
                          Safety Orders
                        </NavLink>
                      </NavItem>
                      <NavItem>
                        <NavLink
                          className={
                            this.state.activeTab === "take-profit"
                              ? "active"
                              : ""
                          }
                          onClick={() => this.toggle("take-profit")}
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
                          <SymbolSearch
                            name="Pair"
                            label="Select pair"
                            options={this.props.symbols}
                            selected={this.state.pair}
                            handleChange={this.handlePairChange}
                            handleBlur={this.handlePairBlur}
                          />
                        </Col>
                        <Col md="6" sm="12">
                          <Label htmlFor="name">Name</Label>
                          <Input
                            type="text"
                            name="name"
                            onChange={this.handleChange}
                            value={this.state.name}
                          />
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label htmlFor="strategy">
                            Strategy<span className="u-required">*</span>
                          </Label>
                          <Input
                            type="select"
                            name="strategy"
                            onChange={this.handleStrategy}
                            onBlur={this.handleBlur}
                            value={this.state.strategy}
                          >
                            <option defaultChecked value="long">
                              Long
                            </option>
                            <option value="short">Short</option>
                          </Input>
                          <small>
                            Long for trends. Short for vertical movement.
                          </small>
                        </Col>
                        <Col md="6" sm="12">
                          <label htmlFor="base_order_size">
                            Base order size<span className="u-required">*</span>
                          </label>
                          <Input
                            // invalid={this.state.baseOrderSizeError}
                            type="text"
                            name="base_order_size"
                            onChange={this.handleBaseChange}
                            onBlur={this.handleBlur}
                            value={this.state.base_order_size}
                          />
                          <FormFeedback valid={!this.state.baseOrderSizeError}>
                            Not enough balance
                          </FormFeedback>
                          <Badge color="secondary" onClick={this.addAll}>
                            All
                          </Badge>
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <label htmlFor="deal_min_value">
                            Deal minimum value
                          </label>
                          <Input
                            type="text"
                            name="deal_min_value"
                            onChange={this.handleChange}
                            value={this.state.deal_min_value}
                          />
                        </Col>
                        <Col md="6" sm="12">
                          <label htmlFor="cooldown">Cooldown</label>
                          <Input
                            type="text"
                            name="cooldown"
                            onChange={this.handleChange}
                            value={this.state.cooldown}
                          />
                        </Col>
                      </Row>
                    </TabPane>

                    {/*
                      Safey orders tab
                    */}
                    <TabPane tabId="safety-orders">
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <Label htmlFor="max_so_count">
                            Maximum number of Safety Orders
                          </Label>
                          <Input
                            invalid={this.state.maxSOCountError}
                            type="text"
                            name="max_so_count"
                            onChange={this.handleChange}
                            onBlur={this.handleBlur}
                            value={this.state.max_so_count}
                          />
                          <FormFeedback>
                            <strong>Safety order size</strong> is required.
                          </FormFeedback>
                          <small>
                            If value = 0, Safety orders will be turned off
                          </small>
                        </Col>
                        {parseInt(this.state.max_so_count) > 0 && (
                          <Col md="6" sm="12">
                            <Label for="so_size">Safety order size</Label>
                            <Input
                              invalid={this.state.soSizeError}
                              type="text"
                              name="so_size"
                              id="so_size"
                              onChange={this.handleSafety}
                              onBlur={this.handleBlur}
                              value={this.state.so_size}
                            />
                            <FormFeedback>
                              <strong>Safety order size</strong> is required.
                            </FormFeedback>
                          </Col>
                        )}
                      </Row>
                      <Row className="u-margin-bottom">
                        {parseInt(this.state.max_so_count) > 0 && (
                          <Col md="10" sm="12">
                            <Label htmlFor="price_deviation_so">
                              Price deviation (%)
                            </Label>
                            <Input
                              invalid={this.state.priceDevSoError}
                              type="text"
                              name="price_deviation_so"
                              id="price_deviation_so"
                              onChange={this.handleChange}
                              onBlur={this.handleBlur}
                              value={this.state.price_deviation_so}
                            />
                            <FormFeedback>
                              <strong>Price deviation</strong> is required.
                            </FormFeedback>
                            <small>
                              How much does the price have to drop to create a
                              Safety Order?
                            </small>
                          </Col>
                        )}
                      </Row>
                    </TabPane>

                    {/*
                      Take profit tab
                    */}
                    <TabPane tabId="take-profit">
                      <Row className="u-margin-bottom">
                        <Col md="8" sm="12">
                          <Label for="take_profit">
                            Take profit at (%):{" "}
                            <span className="u-required">*</span>
                          </Label>
                          <Input
                            invalid={this.state.takeProfitError}
                            type="text"
                            name="take_profit"
                            id="take_profit"
                            onChange={this.handleChange}
                            onBlur={this.handleBlur}
                            value={this.state.take_profit}
                          />
                          <FormFeedback>
                            <strong>Take profit</strong> is required.
                          </FormFeedback>
                        </Col>
                      </Row>
                      <Row className="u-margin-bottom">
                        <Col md="6" sm="12">
                          <label>Trailling</label>
                          <Button
                            color={
                              this.state.trailling === "true"
                                ? "success"
                                : "secondary"
                            }
                            onClick={() =>
                              this.setState({
                                trailling:
                                  this.state.trailling === "true"
                                    ? "false"
                                    : "true",
                              })
                            }
                          >
                            {this.state.trailling === "true" ? "On" : "Off"}
                          </Button>
                        </Col>
                        {this.state.trailling === "true" && (
                          <Col md="6" sm="12">
                            <Label htmlFor="trailling_deviation">
                              Trailling deviation (%)
                            </Label>
                            <Input
                              type="text"
                              name="trailling_deviation"
                              onChange={this.handleChange}
                              onBlur={this.handleBlur}
                              value={this.state.trailling_deviation}
                            />
                          </Col>
                        )}
                      </Row>
                    </TabPane>
                  </TabContent>
                  <Row>
                    {this.state.active === "true" ? (
                      <ButtonToggle
                        color="success"
                        onClick={() => this.props.deactivateBot(this.state._id)}
                      >
                        Deactivate
                      </ButtonToggle>
                    ) : (
                      <div className="update ml-auto mr-auto">
                        <Button
                          className="btn-round"
                          color="primary"
                          type="submit"
                        >
                          Save and activate
                        </Button>
                      </div>
                    )}
                  </Row>
                  {!this.state.formIsValid && (
                    <Row>
                      <Col md="12">
                        <Alert color="danger">
                          <p>There are fields with errors</p>
                          <ul>
                            {this.state.pairError && <li>Pair</li>}
                            {this.state.baseOrderSizeError && (
                              <li>Base order size</li>
                            )}
                            {this.state.soSizeError && (
                              <li>Safety order size</li>
                            )}
                            {this.state.priceDevSoError && (
                              <li>Price deviation</li>
                            )}
                            {this.state.takeProfitError && <li>Take profit</li>}
                            {this.state.traillingDeviationError && (
                              <li>Trailling deviation</li>
                            )}
                          </ul>
                        </Alert>
                      </Col>
                    </Row>
                  )}
                </CardBody>
              </Card>
            </Col>
            <Col md="5" sm="12">
              <BalanceAnalysis
                balances={this.props.balances}
                balance_usage={this.state.balance_usage}
                balance_available={this.state.balance_available}
                balance_available_asset={this.state.balance_available_asset}
              />
            </Col>
          </Row>
        </Form>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: balances } = state.balanceReducer;
  const { data: symbols } = state.symbolReducer;
  const { data: symbolInfo } = state.symbolInfoReducer;
  const { data: bot } = state.getSingleBotReducer;
  const { data: candlestick } = state.candlestickReducer;
  const { botId } = state.botReducer;
  return {
    balances: balances,
    symbols: symbols,
    symbolInfo: symbolInfo,
    bot: bot,
    candlestick: candlestick,
    newBotId: botId
  };
};

export default connect(mapStateToProps, {
  getBalance,
  getSymbols,
  getSymbolInfo,
  createBot,
  getBot,
  editBot,
  activateBot,
  deactivateBot,
  loadCandlestick,
})(BotForm);
