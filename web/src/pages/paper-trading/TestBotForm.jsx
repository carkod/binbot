import { TVChartContainer } from "binbot-charts";
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
import LogsInfo from "../../components/LogsInfo";
import MainTab from "../../components/MainTab";
import SafetyOrdersTab from "../../components/SafetyOrdersTab";
import {
  updateOrderLines,
  updateTimescaleMarks,
} from "../../components/services/charting.service";
import StopLossTab from "../../components/StopLossTab";
import TakeProfitTab from "../../components/TakeProfitTab";
import { getBalanceRaw, getEstimate } from "../../state/balances/actions";
import { defaultSo } from "../../state/constants";
import { checkBalance, checkValue } from "../../validations.js";
import { getSymbolInfo, getSymbols } from "../bots/actions";
import {
  activateTestBot,
  createTestBot,
  deactivateTestBot,
  editTestBot,
  getTestBot,
  setBotState,
} from "./actions";
import { convertGBP, getQuoteAsset } from "./requests";

class TestBotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      id: props.match.params.id ? props.match.params.id : null,
      bot_profit: 0,
      activeTab: "main",
      toggleIndicators: true,
      soPriceDeviation: 0,
      // Chart state
      currentChartPrice: 0,
      currentOrderLines: [],
      currentTimeMarks: [],
    };
  }

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getSymbols();
    this.props.getEstimate();
    if (!checkValue(this.props.match.params.id)) {
      this.props.getTestBot(this.props.match.params.id);
    }
    if (!checkValue(this.props.match.params?.symbol)) {
      this.props.getTestBot({
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
      !checkValue(this.props.bot.pair) &&
      this.props.bot.pair !== p.bot.pair
    ) {
      getQuoteAsset(this.props.bot.pair).then(({ data }) =>
        this.props.setBotState({ quoteAsset: data })
      );
      const currentDate = moment().toISOString();
      this.props.setBotState({
        name: `${this.props.bot.pair}_${currentDate}`,
      });
    }

    if (
      Object.keys(this.props.bot.deal).length > 0 &&
      !checkValue(this.props.bot.base_order_size) &&
      this.props.bot.deal !== p.bot.deal
    ) {
      let currentPrice =
        this.state.currentChartPrice ||
        parseFloat(this.props.bot.deal.current_price);
      if (this.props.bot.deal.buy_price) {
        const buyPrice = parseFloat(this.props.bot.deal.buy_price);

        if (
          this.props.bot.status === "completed" &&
          !checkValue(this.props.bot.deal.sell_price)
        ) {
          currentPrice = this.props.bot.deal.sell_price;
        }

        const profitChange = ((currentPrice - buyPrice) / buyPrice) * 100;

        this.setState({ bot_profit: profitChange.toFixed(4) });
      } else {
        this.setState({ bot_profit: 0 });
      }
    }

    if (
      !checkValue(this.props.bot.orders) &&
      this.props.bot.orders !== p.bot.orders
    ) {
      const currentTimeMarks = updateTimescaleMarks(this.props.bot);
      this.setState({ currentTimeMarks: currentTimeMarks });
    }

    if (this.props.bot.trailling !== p.bot.trailling) {
      const newOrderLines = updateOrderLines(
        this.props.bot,
        this.state.currentChartPrice
      );
      this.setState(
        produce(this.state, (draft) => {
          draft.currentOrderLines = newOrderLines;
        })
      );
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

  handleSubmit = async (e) => {
    e.preventDefault();
    const validation = this.requiredinValidation();
    if (validation) {
      let form = {
        status: this.props.bot.status,
        base_order_size: this.props.bot.base_order_size,
        balance_to_use: this.props.bot.balance_to_use,
        mode: "manual", // Always manual in terminal.binbot
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
        candlestick_interval: this.props.bot.candlestick_interval,
        stop_loss: this.props.bot.stop_loss,
        cooldown: this.props.bot.cooldown,
        safety_orders: this.props.bot.safety_orders,
        strategy: this.props.bot.strategy,
        short_buy_price: this.props.bot.short_buy_price,
        short_sell_price: this.props.bot.short_sell_price,
      };
      if (!checkValue(this.props.match.params.id)) {
        form.id = this.props.match.params.id;
        await this.props.editTestBot(this.props.match.params.id, form);
      } else {
        await this.props.createTestBot(form);
      }
      window.location.reload();
    }
  };

  toggle = (tab) => {
    const { activeTab } = this.state;
    if (activeTab !== tab) this.setState({ activeTab: tab });
  };

  handlePairChange = (value) => {
    // Get pair base or quote asset and set new pair
    if (!checkValue(value)) {
      this.props.setBotState({ pair: value[0] });
    }
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

  handleBlur = (e) => {
    const { name, value } = e.target;
    if (name === "pair") {
      this.props.getSymbolInfo(value);
    }

    // Update charts
    const newOrderLines = updateOrderLines(
      this.props.bot,
      this.state.currentChartPrice
    );
    this.setState(
      produce(this.state, (draft) => {
        draft.currentOrderLines = newOrderLines;
      })
    );
  };

  handleActivation = (e) => {
    const validation = this.requiredinValidation();
    if (validation) {
      this.handleSubmit(e);
      this.props.activateTestBot(this.state.id);
      this.props.getTestBot(this.props.match.params.id);
      if (this.props.match.params.id) {
        this.props.history.push(
          `/admin/paper-trading/edit/${this.props.match.params.id}`
        );
      } else {
        this.props.history.push(`/admin/paper-trading/edit/${this.state.id}`);
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
      const safety_orders = produce(this.props.bot, (draft) => {
        draft.safety_orders[e.target.dataset.index][e.target.name] =
          e.target.value;
      });
      this.props.setBotState(safety_orders);
    }
    return;
  };

  addSo = () => {
    const safety_orders = produce(this.props.bot, (draft) => {
      if (Object.getPrototypeOf(draft.safety_orders) === Object.prototype) {
        draft.safety_orders = [defaultSo];
      } else {
        let newSo = { ...defaultSo };
        newSo.name = `so_${draft.safety_orders.length + 1}`;
        draft.safety_orders.push(newSo);
      }
    });
    this.props.setBotState(safety_orders);
  };

  removeSo = (e) => {
    e.preventDefault();
    const safety_orders = produce(this.props.bot, (draft) => {
      draft.safety_orders.splice(e.target.dataset.index, 1);
    });
    this.props.setBotState(safety_orders);
  };

  handleInitialPrice = (price) => {
    if (!this.props.bot.deal.buy_price && this.props.bot.status !== "active") {
      this.setState(
        produce(this.state, (draft) => {
          draft.currentChartPrice = parseFloat(price);
        })
      );
    }
    const newOrderLines = updateOrderLines(this.props.bot, price);
    this.setState(
      produce(this.state, (draft) => {
        draft.currentOrderLines = newOrderLines;
        draft.currentChartPrice = parseFloat(price);
      })
    );
  };

  updatedPrice = (price) => {
    if (parseFloat(this.state.currentChartPrice) !== parseFloat(price)) {
      const newOrderLines = updateOrderLines(this.props.bot, price);
      this.setState(
        produce(this.state, (draft) => {
          draft.currentOrderLines = newOrderLines;
          draft.currentChartPrice = parseFloat(price);
        })
      );
    }
  };

  render() {
    return (
      <div className="content">
        <Row>
          <Col md="12">
            <Card style={{ minHeight: "650px" }}>
              <CardHeader>
                <Row style={{ alignItems: "baseline" }}>
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
                      )}{" "}
                      {!checkValue(this.props.bot.strategy) && (
                        <Badge color="info">{this.props.bot.strategy}</Badge>
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
              </CardHeader>
              <CardBody>
                {!checkValue(this.props.bot?.pair) && (
                  <TVChartContainer
                    symbol={this.props.bot.pair}
                    interval={this.props.bot.interval}
                    timescaleMarks={this.state.currentTimeMarks}
                    orderLines={this.state.currentOrderLines}
                    onTick={(tick) => this.updatedPrice(tick.close)}
                    getLatestBar={(bar) => this.handleInitialPrice(bar[3])}
                  />
                )}
              </CardBody>
            </Card>
          </Col>
        </Row>
        <Row>
          {!checkValue(this.props.bot) &&
          this.props.bot.orders.length > 0 &&
          !checkValue(this.props.match.params.id) ? (
            <>
              <Col md="7" sm="12">
                <BotInfo bot={this.props.bot} />
              </Col>
              {this.props.bot.errors.length > 0 && (
                <Col md="4" sm="12">
                  <LogsInfo info={this.props.bot.errors} />
                </Col>
              )}
            </>
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
                      bot={this.props.bot}
                      handlePairChange={this.handlePairChange}
                      handlePairBlur={this.handleBlur}
                      handleChange={this.handleChange}
                      handleBaseChange={this.handleBaseChange}
                      handleBlur={this.handleBlur}
                      addMin={this.addMin}
                      addAll={this.addAll}
                      baseOrderSizeInfoText="Not important, real funds not used"
                    />

                    <SafetyOrdersTab
                      safetyOrders={this.props.bot.safety_orders}
                      asset={this.props.bot.pair}
                      quoteAsset={this.props.bot.quoteAsset}
                      soPriceDeviation={this.state.soPriceDeviation}
                      handleChange={this.handleSoChange}
                      handleBlur={this.handleBlur}
                      addSo={this.addSo}
                      removeSo={this.removeSo}
                    />

                    <StopLossTab
                      stop_loss={this.props.bot.stop_loss}
                      stopLossError={this.props.bot.stopLossError}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                    />

                    <TakeProfitTab
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
                        disabled={checkValue(this.props.bot?.id)}
                      >
                        {this.props.bot.status === "active" &&
                        Object.keys(this.props.bot.deal).length > 0
                          ? "Update deal"
                          : "Deal"}
                      </ButtonToggle>
                    </Col>
                    <Col>
                      {(this.props.bot.status !== "active" ||
                        Object.keys(this.props.bot.deal).length === 0) && (
                        <Button
                          className="btn-round"
                          color="primary"
                          type="submit"
                        >
                          Save
                        </Button>
                      )}
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
              {this.props.balance_estimate && this.props.balance_raw ? (
                <BalanceAnalysis
                  balance={this.props.balance_estimate}
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
  const { data: balance_raw } = state.balanceRawReducer;
  const { data: symbols } = state.symbolReducer;
  const { bot, createdBotId } = state.testBotsReducer;
  const { loading } = state.loadingReducer;
  const { data: balanceEstimate } = state.estimateReducer;

  return {
    balance_estimate: balanceEstimate,
    balance_raw: balance_raw,
    symbols: symbols,
    bot: bot,
    loading: loading,
    createdBotId: createdBotId,
  };
};

export default connect(mapStateToProps, {
  getEstimate,
  getBalanceRaw,
  getSymbols,
  getSymbolInfo,
  createTestBot,
  getTestBot,
  editTestBot,
  activateTestBot,
  deactivateTestBot,
  setBotState,
})(TestBotForm);
