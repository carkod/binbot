import produce from "immer";
import moment from "moment";
import React from "react";
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
  Nav,
  NavItem,
  NavLink,
  Row,
  TabContent,
} from "reactstrap";
import BalanceAnalysis from "../../components/BalanceAnalysis";
import BotInfo from "../../components/BotInfo";
import Candlestick from "../../components/Candlestick";
import IndicatorsButtons from "../../components/IndicatorsButtons";
import { getBalance, getBalanceRaw } from "../../state/balances/actions";
import { defaultSo } from "../../state/constants";
import {
  checkBalance,
  checkValue,
  intervalOptions,
} from "../../validations.js";
import { getSymbolInfo, getSymbols, loadCandlestick } from "../bots/actions";
import {
  activateTestBot,
  createTestBot,
  deactivateTestBot,
  editTestBot,
  getTestBot,
  setBotState,
} from "./actions";
import { convertGBP, getQuoteAsset } from "./requests";
import MainTab from "./tabs/Main";
import SafetyOrders from "./tabs/SafetyOrders";
import StopLoss from "./tabs/StopLoss";
import TakeProfit from "./tabs/TakeProfit";

class TestBotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      _id: props.match.params.id ? props.match.params.id : null,
      bot_profit: 0,
      activeTab: "main",
      toggleIndicators: true,
      soPriceDeviation: 0,
    };
  }

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getBalance();
    this.props.getSymbols();
    if (!checkValue(this.props.match.params.id)) {
      this.props.getTestBot(this.props.match.params.id);
    }
    if (!checkValue(this.props.match.params?.symbol)) {
      this.props.setBotState({
        pair: this.props.match.params.symbol,
      });
    }
  };

  componentDidUpdate = (p, s) => {
    if (
      !checkValue(this.props.createdBotId) &&
      this.props.createdBotId !== p.createdBotId
    ) {
      this.props.history.push(
        `/admin/paper-trading/edit/${this.props.createdBotId}`
      );
    }
    if (
      (!checkValue(this.props.bot.pair) &&
        this.props.bot.pair !== p.bot.pair) ||
      this.props.bot.candlestick_interval !== p.bot.candlestick_interval
    ) {
      const interval = !checkValue(this.props.history.location.state)
        ? this.props.history.location.state.candlestick_interval
        : this.props.bot.candlestick_interval;
      this.props.loadCandlestick(
        this.props.bot.pair,
        interval,
        this.props.bot?.deal?.buy_timestamp
      );
      getQuoteAsset(this.props.bot.pair).then(({ data }) =>
        this.props.setBotState({ quoteAsset: data })
      );
      const currentDate = moment().toISOString();
      this.props.setBotState({
        name: `${this.props.bot.pair}_${currentDate}`,
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
          let currentPrice = parseFloat(this.props.bot.deal.current_price);
          const buyPrice = parseFloat(this.props.bot.deal.buy_price);
          const profitChange = ((currentPrice - buyPrice) / buyPrice) * 100;
          if (
            this.props.bot.status === "completed" &&
            !checkValue(this.props.bot.deal.sell_price)
          ) {
            currentPrice = this.props.bot.deal.sell_price;
          }
          this.setState({ bot_profit: profitChange.toFixed(4) });
        } else {
          this.setState({ bot_profit: 0 });
        }
      }
    }
  };

  requiredinValidation = () => {
    const { pair, take_profit, trailling, trailling_deviation, stop_loss } =
      this.props.bot;

    // If everything below is ok, form will be valid
    this.props.setBotState({ formIsValid: true });

    if (checkValue(pair)) {
      this.props.setBotState({ pairError: true, formIsValid: false });
      return false;
    } else {
      this.props.setBotState({ pairError: false });
    }

    if (checkValue(take_profit) && checkBalance(take_profit)) {
      this.props.setBotState({ takeProfitError: true, formIsValid: false });
      return false;
    } else {
      this.props.setBotState({ takeProfitError: false });
    }

    if (!checkValue(stop_loss)) {
      if (parseFloat(stop_loss) > 100 || parseFloat(stop_loss) < 0) {
        this.props.setBotState({ stopLossError: true, formIsValid: false });
      } else {
        this.props.setBotState({ stopLossError: false });
      }
    }

    if (trailling === "true") {
      if (
        checkBalance(trailling_deviation) &&
        checkBalance(trailling_deviation)
      ) {
        this.props.setBotState({
          traillingDeviationError: true,
          formIsValid: false,
        });
        return false;
      } else {
        this.props.setBotState({ traillingDeviationError: false });
      }
    }

    return true;
  };

  handleSubmit = (e) => {
    e.preventDefault();
    const validation = this.requiredinValidation();
    if (validation) {
      let form = {
        status: this.props.bot.status,
        balance_size_to_use: this.props.bot.balance_size_to_use, // Centralized
        base_order_size: this.props.bot.base_order_size,
        balance_to_use: this.props.bot.balance_to_use,
        mode: "manual",
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
        candlestick_interval: this.props.bot.candlestick_interval,
        orders: this.props.bot.orders,
        stop_loss: this.props.bot.stop_loss,
        cooldown: this.props.bot.cooldown,
        safety_orders: this.props.bot.safety_orders
      };
      if (!checkValue(this.props.match.params.id)) {
        form._id = this.props.match.params.id;
        this.props.editTestBot(form);
      } else {
        this.props.createTestBot(form);
      }
    }
  };

  toggle = (tab) => {
    const { activeTab } = this.state;
    if (activeTab !== tab) this.setState({ activeTab: tab });
  };

  handlePairChange = (value) => {
    // Get pair base or quote asset and set new pair
    if (!checkValue(value)) {
      this.props.getSymbolInfo(value[0]);
      this.props.setBotState({ pair: value[0] });
    }
  };

  handleStrategy = (e) => {
    // Get pair base or quote asset and set new strategy
    const { pair } = this.state;
    this.props.getSymbolInfo(pair);
    this.props.setBotState({ [e.target.name]: e.target.value });
  };

  handleBaseChange = (e) => {
    this.props.setBotState({
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
      this.props.setBotState({ base_order_size: minAmount });
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
            this.props.setBotState({
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
        this.props.setBotState({ addAllError: "No balance available to add" });
      } else {
        this.props.setBotState({ base_order_size: totalBalance });
      }
    }
  };

  handleSafety = (e) => {
    const { pair } = this.props;
    this.props.getSymbolInfo(pair);
    this.props.setBotState({
      [e.target.name]: e.target.value,
    });
  };

  handleChange = (e) => {
    e.preventDefault();
    this.props.setBotState({
      [e.target.name]: e.target.value,
    });
  };

  handleBlur = () => {
    if (
      !checkValue(this.props.bot.pair) &&
      !checkValue(this.props.bot.candlestick_interval)
    ) {
      this.props.loadCandlestick(
        this.props.bot.pair,
        this.props.bot.candlestick_interval,
        this.props.bot?.deal?.buy_timestamp
      );
    }
  };

  handleActivation = (e) => {
    const validation = this.requiredinValidation();
    if (validation) {
      this.handleSubmit(e);
      this.props.activateTestBot(this.state._id);
      this.props.getTestBot(this.props.match.params.id);
      if (this.props.match.params.id) {
        this.props.history.push(
          `/admin/paper-trading/edit/${this.props.match.params.id}`
        );
      }
    }
  };

  toggleTrailling = () => {
    const value = this.props.bot.trailling === "true" ? "false" : "true";
    this.props.setBotState({
      trailling: value,
    });
  };

  handleToggleIndicator = (value) => {
    this.setState({ toggleIndicators: value });
  };

  handleSoChange = (e) => {
    if (e.target.name === "so_size" || e.target.name === "buy_price") {
      const safety_orders = produce(this.props.bot, draft => {
        draft.safety_orders[e.target.dataset.index][e.target.name] = e.target.value;
      });
      this.props.setBotState(safety_orders)
    }
    return;
  };


  addSo = () => {
    const safety_orders = produce(this.props.bot, draft => {
      if (Object.getPrototypeOf(draft.safety_orders) === Object.prototype) {
        draft.safety_orders = [defaultSo]
      } else {
        let newSo = {...defaultSo}
        newSo.name = `so_${draft.safety_orders.length + 1}`
        draft.safety_orders.push(newSo)
      }
      
    });
    this.props.setBotState(safety_orders)
  }

  removeSo = (e) => {
    e.preventDefault();
    const safety_orders = produce(this.props.bot, draft => {
      draft.safety_orders.splice(e.target.dataset.index, 1)
    });
    this.props.setBotState(safety_orders);
  }

  render() {
    return (
      <div className="content">
        <Row>
          <Col md="12">
            <Card style={{ minHeight: "650px" }}>
              <CardHeader>
                <Row>
                  <Col>
                    <CardTitle tag="h3">
                      {this.props.bot?.pair}{" "}
                      {!checkValue(this.state.bot_profit) && (
                        <Badge
                          color={
                            parseFloat(this.state.bot_profit) > 0
                              ? "success"
                              : "danger"
                          }
                        >
                          {this.state.bot_profit + "%"}
                        </Badge>
                      )}{" "}
                      {!checkValue(this.props.bot.status) && (
                        <Badge
                          color={
                            this.props.bot.status === "active"
                              ? "success"
                              : this.props.bot.status === "error"
                              ? "warning"
                              : this.props.bot.status === "completed"
                              ? "info"
                              : "secondary"
                          }
                        >
                          {this.props.bot.status}
                        </Badge>
                      )}
                    </CardTitle>
                  </Col>
                  <Col>
                    {!checkValue(this.state.bot_profit) &&
                      !isNaN(this.state.bot_profit) && (
                        <h5>
                          Earnings after commissions (est.):{" "}
                          {parseFloat(this.state.bot_profit) - 0.3 + "%"}
                        </h5>
                      )}
                  </Col>
                </Row>
                <br />
                <Row>
                  <Col>
                    {intervalOptions.map((item) => (
                      <Badge
                        key={item}
                        onClick={() => {
                          if (!this.props.bot.pair) {
                            alert("Please, set Pair first");
                          }
                          this.props.setBotState({
                            candlestick_interval: item,
                          });
                        }}
                        color={
                          this.props.bot.candlestick_interval === item
                            ? "primary"
                            : "secondary"
                        }
                        className="btn btn-margin-right"
                      >
                        {item}
                      </Badge>
                    ))}
                  </Col>
                </Row>
                <br />
                <Row>
                  <Col>
                    <IndicatorsButtons
                      toggle={this.state.toggleIndicators}
                      handleChange={this.handleToggleIndicator}
                    />
                  </Col>
                </Row>
              </CardHeader>
              <CardBody>
                {this.props.candlestick && !checkValue(this.props.bot.pair) ? (
                  <Candlestick
                    data={this.props.candlestick}
                    bot={this.props.bot}
                    deal={this.props.bot?.deal}
                    toggleIndicators={this.state.toggleIndicators}
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
                            this.state.activeTab === "safety-orders" ? "active" : ""
                          }
                          onClick={() => this.toggle("safety-orders")}
                        >
                          Safety orders
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
                      state={this.props.bot}
                      handlePairChange={this.handlePairChange}
                      handlePairBlur={this.handleBlur}
                      handleChange={this.handleChange}
                      handleBaseChange={this.handleBaseChange}
                      handleBlur={this.handleBlur}
                      addMin={this.addMin}
                      addAll={this.addAll}
                    />

                    <SafetyOrders
                      safetyOrders={this.props.bot.safety_orders}
                      asset={this.props.bot.pair}
                      quoteAsset={this.props.bot.quoteAsset}
                      soPriceDeviation={this.state.soPriceDeviation}
                      handleChange={this.handleSoChange}
                      addSo={this.addSo}
                      removeSo={this.removeSo}
                    />

                    <StopLoss
                      stop_loss={this.props.bot.stop_loss}
                      stopLossError={this.props.bot.stopLossError}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                    />

                    <TakeProfit
                      takeProfitError={this.props.bot.takeProfitError}
                      take_profit={this.props.bot.take_profit}
                      trailling={this.props.bot.trailling}
                      trailling_deviation={this.props.bot.trailling_deviation}
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
                        disabled={checkValue(this.props.bot?._id)}
                      >
                        {this.props.bot.status === "active" &&
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
                  {!this.props.bot.formIsValid && (
                    <Row>
                      <Col md="12">
                        <Alert color="danger">
                          <p>There are fields with errors</p>
                          <ul>
                            {this.props.bot.pairError && <li>Pair</li>}
                            {this.props.bot.baseOrderSizeError && (
                              <li>Base order size</li>
                            )}
                            {this.props.bot.baseOrderSizeError && (
                              <>
                                <li>
                                  Base order size (How much to trade?) must be
                                  filled
                                </li>
                              </>
                            )}
                            {this.props.bot.soSizeError && (
                              <>
                                <li>Safety order size</li>
                                <li>Check balance for Safety order size</li>
                              </>
                            )}
                            {this.props.bot.priceDevSoError && (
                              <li>Price deviation</li>
                            )}
                            {this.props.bot.takeProfitError && (
                              <li>Take profit</li>
                            )}
                            {this.props.bot.traillingDeviationError && (
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
              {this.props.lastBalance && this.props.balance_raw ? (
                <BalanceAnalysis
                  balance={this.props.lastBalance}
                  balance_raw={this.props.balance_raw}
                />
              ) : (
                ""
              )}
            </Col>
          </Row>
        </Form>
      </div>
    );
  }
}

const mapStateToProps = (state, props) => {
  let { data: balance } = state.balanceReducer;
  const { data: balance_raw } = state.balanceRawReducer;
  const { data: symbols } = state.symbolReducer;
  const { bot, createdBotId } = state.testBotsReducer;
  const { data: candlestick } = state.candlestickReducer;
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
    loading: loading,
    createdBotId: createdBotId,
  };
};

export default connect(mapStateToProps, {
  getBalance,
  getBalanceRaw,
  getSymbols,
  getSymbolInfo,
  createTestBot,
  getTestBot,
  editTestBot,
  activateTestBot,
  deactivateTestBot,
  loadCandlestick,
  setBotState,
})(TestBotForm);
