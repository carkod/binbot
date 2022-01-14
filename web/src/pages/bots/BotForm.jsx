import React from "react";
import produce from "immer";
import { nanoid } from "nanoid";
import moment from "moment";
import { connect } from "react-redux";
import {
  Alert,
  Badge,
  Button,
  ButtonToggle,
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
} from "reactstrap";
import BalanceAnalysis from "../../components/BalanceAnalysis";
import BotInfo from "../../components/BotInfo";
import Candlestick from "../../components/Candlestick";
import { getBalance, getBalanceRaw } from "../../state/balances/actions";
import {
  checkBalance,
  checkValue,
  intervalOptions,
} from "../../validations.js";
import {
  activateBot,
  createBot,
  deactivateBot,
  editBot,
  getBot,
  getSymbolInfo,
  getSymbols,
  loadCandlestick,
} from "./actions";
import { ErrorLog } from "./ErrorLog";
import { convertGBP, getQuoteAsset } from "./requests";
import SafetyOrderField from "./SafetyOrderField";
import MainTab from "./tabs/Main";
import StopLoss from "./tabs/StopLoss";
import TakeProfit from "./tabs/TakeProfit";

class BotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      _id: props.match.params.id ? props.match.params.id : null,
      active: false,
      status: "inactive",
      balance_available: "0",
      balance_available_asset: "",
      balanceAvailableError: false,
      balanceUsageError: false,
      balance_usage_size: "100", // Centralized
      base_order_size: "",
      baseOrderSizeError: false,
      balance_to_use: "GBP",
      bot_profit: 0,
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
      formIsValid: true,
      activeTab: "main",
      candlestick_interval: intervalOptions[11],
      deals: [],
      orders: [],
      quoteAsset: "",
      baseAsset: "",
      stop_loss: 0,
      stopLossError: false,
      safety_orders: {},
    };
  }

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getBalance();
    this.props.getSymbols();
    if (!checkValue(this.props.match.params.id)) {
      this.props.getBot(this.props.match.params.id);
      this.computeAvailableBalance();
    }
  };

  componentDidUpdate = (p, s) => {
    if (p.symbolInfo !== this.props.symbolInfo) {
      this.computeAvailableBalance();
    }

    if (p.bot !== this.props.bot) {
      this.setState({
        status: this.props.bot.status,
        balance_usage_size: this.props.bot.balance_usage_size,
        balance_to_use: this.props.bot.balance_to_use,
        base_order_size: this.props.bot.base_order_size,
        max_so_count: this.props.bot.max_so_count,
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        price_deviation_so: this.props.bot.price_deviation_so,
        so_size: this.props.bot.so_size,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
        orders: this.props.bot.orders,
        stop_loss: this.props.bot.stop_loss,
        safety_orders: this.props.bot.safety_orders,
        candlestick_interval: !checkValue(this.props.bot.candlestick_interval)
          ? this.props.bot.candlestick_interval
          : intervalOptions[11],
      });
    }
    if (
      !checkValue(this.state.pair) &&
      s.candlestick_interval !== this.state.candlestick_interval
    ) {
      this.props.loadCandlestick(
        this.state.pair,
        this.state.candlestick_interval
      );
    }
    // If there is a newBotId, it means form was created
    // To make sure of this, check also URL has NO id param
    if (
      !checkValue(this.props.newBotId) &&
      this.props.newBotId !== p.newBotId &&
      checkValue(this.props.match.params.id)
    ) {
      this.props.history.push({
        pathname: `/admin/bots-edit/${this.props.newBotId}`,
        state: { candlestick_interval: this.state.candlestick_interval },
      });
    }

    // Only for edit bot page
    // Fill up the candlestick when pair is available and inherit the interval too
    if (!checkValue(this.state.pair) && this.state.pair !== s.pair) {
      const interval = !checkValue(this.props.history.location.state)
        ? this.props.history.location.state.candlestick_interval
        : this.state.candlestick_interval;
      this.props.loadCandlestick(this.state.pair, interval);
      getQuoteAsset(this.state.pair).then(({ data }) =>
        this.setState({ quoteAsset: data })
      );
      const currentDate = moment().toISOString();
      this.setState({
        name: `${this.state.pair}_${currentDate}`,
      });
    }

    if (
      this.props.botActive !== p.botActive &&
      !checkValue(this.props.match.params.id)
    ) {
      this.props.getBot(this.props.match.params.id);
    }

    // Candlestick data updates
    if (
      !checkValue(this.props.candlestick) &&
      this.props.candlestick !== p.candlestick &&
      this.props.candlestick.error !== 1 &&
      !checkValue(this.props.bot)
    ) {
      const { trace } = this.props.candlestick;
      if (trace.length > 0) {
        if (
          !checkValue(this.props.bot) &&
          !checkValue(this.props.bot.deal) &&
          Object.keys(this.props.bot.deal).length > 0 &&
          !checkValue(this.props.bot.base_order_size)
        ) {
          const currentPrice = parseFloat(this.props.bot.deal.current_price);
          const buyPrice = parseFloat(this.props.bot.deal.buy_price);
          const profitChange = ((currentPrice - buyPrice) / buyPrice) * 100;
          this.setState({ bot_profit: profitChange.toFixed(4) });
        } else {
          this.setState({ bot_profit: 0 });
        }
      }
    }

    if (
      this.state.quoteAsset !== s.quoteAsset &&
      !checkValue(this.props.balances)
    ) {
      this.computeAvailableBalance();
    }
  };

  requiredinValidation = () => {
    const {
      pair,
      base_order_size,
      take_profit,
      max_so_count,
      so_size,
      trailling,
      trailling_deviation,
      stop_loss,
    } = this.state;

    // If everything below is ok, form will be valid
    this.setState({ formIsValid: true });

    if (checkValue(pair)) {
      this.setState({ pairError: true, formIsValid: false });
      return false;
    } else {
      this.setState({ pairError: false });
    }

    if (checkValue(base_order_size)) {
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

    if (!checkValue(stop_loss)) {
      if (parseFloat(stop_loss) > 100 || parseFloat(stop_loss) < 0) {
        this.setState({ stopLossError: true, formIsValid: false });
      } else {
        this.setState({ stopLossError: false });
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

  handleSubmit = (e) => {
    e.preventDefault();
    const validation = this.requiredinValidation();
    if (validation) {
      const form = {
        status: this.state.status,
        balance_to_use: this.state.balance_to_use,
        base_order_size: String(this.state.base_order_size),
        max_so_count: this.state.max_so_count,
        name: this.state.name,
        pair: this.state.pair,
        take_profit: this.state.take_profit,
        trailling: this.state.trailling,
        trailling_deviation: this.state.trailling_deviation,
        stop_loss: this.state.stop_loss,
        safety_orders: this.state.safety_orders,
        candlestick_interval: this.state.candlestick_interval,
      };
      if (this.state._id === null) {
        this.props.createBot(form);
      } else {
        this.props.editBot(this.state._id, form);
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
    const { base_order_size, safety_orders, short_order } = this.state;
    const { balances } = this.props;

    let value = "0";
    let name = "";
    if (!checkValue(this.state.quoteAsset) && !checkValue(balances)) {
      balances.forEach((x) => {
        if (this.state.quoteAsset === x.asset) {
          value = x.free;
          name = x.asset;
        }
      });

      if (
        !checkValue(value) &&
        !checkBalance(value) &&
        Object.values(safety_orders).length > 0 &&
        this.props.bot
      ) {
        const baseOrder = parseFloat(base_order_size) * 1; // base order * 100% of all balance
        const safetyOrders = Object.values(safety_orders).reduce(
          (v, a) => {
            return parseFloat(v.so_size) + parseFloat(a.so_size);
          },
          { so_size: 0 }
        );
        const shortOrder = parseFloat(short_order);
        const checkBaseOrder = this.props.bot.orders.find(
          (x) => x.deal_type === "base_order"
        );
        let updatedValue = value - (baseOrder + safetyOrders + shortOrder);
        if (!checkValue(checkBaseOrder) && "deal_type" in checkBaseOrder) {
          updatedValue = baseOrder + updatedValue;
        }
        updatedValue.toFixed(8);

        // Check that we have enough funds
        // If not return error
        if (parseFloat(updatedValue) > 0) {
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

  handlePairBlur = () => {
    if (!checkValue(this.state.pair)) {
      this.props.loadCandlestick(
        this.state.pair,
        this.state.candlestick_interval
      );
    }
  };

  handleStrategy = (e) => {
    // Get pair base or quote asset and set new strategy
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.setState({ [e.target.name]: e.target.value });
  };

  handleBaseChange = (e) => {
    this.setState({
      base_order_size: e.target.value,
    });
  };

  addMin = () => {
    const { pair, quoteAsset } = this.state;
    if (!checkValue(pair)) {
      this.props.getSymbolInfo(pair);
      let minAmount = "";
      switch (quoteAsset) {
        case "BTC":
          minAmount = 0.001;
          break;
        case "BNB":
          minAmount = 0.051;
          break;
        case "GBP":
          minAmount = 10;
          break;
        default:
          break;
      }
      this.setState({ base_order_size: minAmount });
    }
  };

  addAll = async () => {
    const { pair, quoteAsset } = this.state;
    const { balance_raw: balances } = this.props;
    if (!checkValue(pair) && balances?.length > 0) {
      this.props.getSymbolInfo(pair);
      let totalBalance = 0;
      for (let x of balances) {
        if (x.asset === "GBP") {
          const rate = await convertGBP(quoteAsset + "GBP");
          if ("code" in rate.data) {
            this.setState({
              addAllError: "Conversion for this crypto not available",
            });
          }
          const cryptoBalance =
            parseFloat(x.free) / parseFloat(rate.data.price);
          totalBalance += parseFloat(
            Math.floor(cryptoBalance * 100000) / 100000
          );
        }
        if (x.asset === quoteAsset) {
          totalBalance += parseFloat(x.free);
        }
      }

      if (totalBalance <= 0) {
        this.setState({ addAllError: "No balance available to add" });
      } else {
        this.setState({ base_order_size: totalBalance });
      }
    }
  };

  handleSafety = (e) => {
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.setState({ [e.target.name]: e.target.value });
  };

  handleChange = (e) => {
    e.preventDefault();
    this.setState({ [e.target.name]: e.target.value });
  };

  handleBlur = () => {
    if (!checkValue(this.state.pair)) {
      this.props.loadCandlestick(
        this.state.pair,
        this.state.candlestick_interval
      );
      this.computeAvailableBalance();
    }
  };

  handleShortOrder = (e) => {
    this.setState({ [e.target.name]: e.target.value });
    if (parseFloat(e.target.value) > 0) {
      this.setState({ strategy: "short" });
    } else {
      this.setState({ strategy: "long" });
    }
  };

  handleActivation = (e) => {
    const validation = this.requiredinValidation();
    if (validation) {
      this.handleSubmit(e);
      this.props.activateBot(this.state._id);
    }
  };

  renderSO = () => {
    const count = parseInt(this.state.max_so_count);
    const length = Object.keys(this.state.safety_orders).length;
    let newState = {};
    if (count > 0 && length === 0) {
      for (let i = 0; i < count; i++) {
        const id = nanoid();
        newState[id] = {
          so_size: "",
          price_deviation_so: "0.63",
          priceDevSoError: false,
          soSizeError: false,
        };
      }
    } else if (count - length > 0) {
      newState = this.state.safety_orders;
      for (let i = 0; i < count - length; i++) {
        const id = nanoid();
        newState[id] = {
          so_size: "",
          price_deviation_so: "0.63",
          priceDevSoError: false,
          soSizeError: false,
        };
      }
    } else if (count - length < 0) {
      newState = this.state.safety_orders;
      for (let i = 0; i < length - count; i++) {
        const id = Object.keys(newState)[length - 1];
        delete newState[id];
      }
    }
    this.setState({ safety_orders: newState });
  };

  handleMaxSoChange = (e) => {
    e.preventDefault();
    const count = parseInt(this.state.max_so_count);
    const value = parseInt(e.target.value);
    if (count !== value) {
      this.setState({ [e.target.name]: e.target.value }, () => this.renderSO());
    }
  };

  handleSoChange = (id) => (e) => {
    e.preventDefault();
    this.setState(
      produce((draft) => {
        draft.safety_orders[id][e.target.name] = e.target.value;
      })
    );
  };

  toggleTrailling = () =>
    this.setState({
      trailling: this.state.trailling === "true" ? "false" : "true",
    });

  render() {
    return (
      <div className="content">
        <Row>
          <Col md="12">
            <Card style={{ minHeight: "650px" }}>
              <CardHeader>
                <CardTitle tag="h3">
                  {this.state.pair}{" "}
                  {!checkValue(this.state.bot_profit) &&
                  !isNaN(this.state.bot_profit) && (
                    <Badge
                      color={
                        parseFloat(this.state.bot_profit) > 0
                          ? "success"
                          : "danger"
                      }
                    >
                      {this.state.bot_profit + "%"}
                    </Badge>
                  )}
                  {' '}
                  {!checkValue(this.state.status) &&
                  <Badge
                      color={
                        this.state.status === "active"
                          ? "success"
                          : this.state.status === "error"
                          ? "warning"
                          : this.state.status === "completed"
                          ? "info"
                          : "secondary"
                      }
                    >
                      {this.state.status}
                    </Badge>
                  }
                  <br />
                  {!checkValue(this.state.bot_profit) &&
                  !isNaN(this.state.bot_profit) &&
                    <small>Earnings after commissions (est.): {parseFloat(this.state.bot_profit) - 0.3 + "%"}</small>
                  }
                  
                </CardTitle>
                <div className="">
                  {intervalOptions.map((item) => (
                    <Badge
                      key={item}
                      onClick={() =>
                        this.setState({ candlestick_interval: item })
                      }
                      color={
                        this.state.candlestick_interval === item
                          ? "primary"
                          : "secondary"
                      }
                      className="btn btn-margin-right"
                    >
                      {item}
                    </Badge>
                  ))}
                </div>
              </CardHeader>
              <CardBody>
                {this.props.candlestick && this.props.candlestick.error !== 1 && !checkValue(this.state.pair) ? (
                  <Candlestick
                    data={this.props.candlestick}
                    bot={this.state}
                    deal={
                      this.props.bot && this.props.bot.deal
                        ? this.props.bot.deal
                        : null
                    }
                  />
                ) : (
                  ""
                )}
              </CardBody>
            </Card>
          </Col>
        </Row>
        <Row>
          {!checkValue(this.props.bot) &&
          this.props.bot.orders.length > 0 &&
          !checkValue(this.props.match.params.id) ? (
            <Col md="7" sm="12">
              <BotInfo bot={this.props.bot} />
            </Col>
          ) : (
            ""
          )}
        </Row>
        <Form onSubmit={this.handleSubmit}>
          <Row>
            <Col md="7" sm="12">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <small>
                      Base order size must be always filled and will always be
                      triggered in activation. Short order will replace base
                      order if it reaches stop price.
                    </small>
                    <br />
                    <br />
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
                            this.state.activeTab === "stop-loss" ? "active" : ""
                          }
                          onClick={() => this.toggle("stop-loss")}
                        >
                          Stop Loss
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
                    Tab contents
                  */}
                  <TabContent activeTab={this.state.activeTab}>
                    <MainTab
                      symbols={this.props.symbols}
                      state={this.state}
                      handlePairChange={this.handlePairChange}
                      handlePairBlur={this.handlePairBlur}
                      handleChange={this.handleChange}
                      handleBaseChange={this.handleBaseChange}
                      handleBlur={this.handleBlur}
                      addMin={this.addMin}
                      addAll={this.addAll}
                    />

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
                            onChange={this.handleMaxSoChange}
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
                      </Row>
                      {parseInt(this.state.max_so_count) > 0 &&
                        Object.keys(this.state.safety_orders).map((so) => (
                          <SafetyOrderField
                            key={so}
                            id={so}
                            price_deviation_so={
                              this.state.safety_orders[so].price_deviation_so
                            }
                            priceDevSoError={
                              this.state.safety_orders[so].priceDevSoError
                            }
                            so_size={this.state.safety_orders[so].so_size}
                            soSizeError={
                              this.state.safety_orders[so].soSizeError
                            }
                            handleChange={this.handleSoChange}
                            handleBlur={this.handleBlur}
                          />
                        ))}
                    </TabPane>

                    <StopLoss
                      stop_loss={this.state.stop_loss}
                      stopLossError={this.state.stopLossError}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                    />

                    <TakeProfit
                      takeProfitError={this.state.takeProfitError}
                      take_profit={this.state.take_profit}
                      trailling={this.state.trailling}
                      trailling_deviation={this.state.trailling_deviation}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                      toggleTrailling={this.toggleTrailling}
                    />
                  </TabContent>
                  <Row xs="2">
                    <Col>
                      <ButtonToggle
                        className="btn-round"
                        color="primary"
                        onClick={this.handleActivation}
                        disabled={checkValue(this.state._id)}
                      >
                        {(this.state.status === "active" ||
                          this.state.active === "true") &&
                        Object.keys(this.props.bot.deal).length > 0
                          ? "Update deal"
                          : "Deal"}
                      </ButtonToggle>
                    </Col>
                    <Col>
                      <Button
                        className="btn-round"
                        color="primary"
                        type="submit"
                      >
                        Save
                      </Button>
                    </Col>
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
                            {this.state.baseOrderSizeError && (
                              <>
                                <li>Base order size (How much to trade?) must be filled</li>
                              </>
                            )}
                            {this.state.soSizeError && (
                              <>
                                <li>Safety order size</li>
                                <li>Check balance for Safety order size</li>
                              </>
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
              {this.props.lastBalance && this.props.balance_raw && (
                <BalanceAnalysis
                  balance={this.props.lastBalance}
                  balance_raw={this.props.balance_raw}
                />
              )}
            </Col>
          </Row>
        </Form>
        {this.props.bot &&
          this.props.bot.errors &&
          this.props.bot.errors.length > 0 && (
            <Row>
              <Col md="12">
                {this.props.bot &&
                  this.props.bot.errors &&
                  this.props.bot.errors.length > 0 && (
                    <ErrorLog errors={this.props.bot.errors} />
                  )}
              </Col>
            </Row>
          )}
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  let { data: balance } = state.balanceReducer;
  const { data: balance_raw } = state.balanceRawReducer;
  const { data: symbols } = state.symbolReducer;
  const { data: bot } = state.getSingleBotReducer;
  const { data: candlestick } = state.candlestickReducer;
  const { botId, botActive } = state.botReducer;
  const { loading } = state.loadingReducer;

  let lastBalance = null;
  if (!checkValue(balance) && balance.length > 0) {
    lastBalance = balance[0];
  }

  return {
    lastBalance: lastBalance,
    balance_raw: balance_raw,
    symbols: symbols,
    bot: bot,
    candlestick: candlestick,
    newBotId: botId,
    botActive: botActive,
    loading: loading,
  };
};

export default connect(mapStateToProps, {
  getBalance,
  getBalanceRaw,
  getSymbols,
  getSymbolInfo,
  createBot,
  getBot,
  editBot,
  activateBot,
  deactivateBot,
  loadCandlestick,
})(BotForm);
