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
import { getBalanceRaw, getEstimate } from "../../state/balances/actions";
import {
  computeSingleBotProfit,
} from "../../state/bots/actions";
import { defaultSo } from "../../state/constants";
import { checkBalance, checkValue, roundDecimals } from "../../validations.js";
import SafetyOrdersTab from "../../components/SafetyOrdersTab";
import {
  activateBot,
  createBot,
  deactivateBot,
  editBot,
  getBot,
  getSymbolInfo,
  getSymbols,
  setBot,
  resetBot,
} from "./actions";
import { convertGBP, getBaseAsset, getQuoteAsset } from "./requests";
import MainTab from "../../components/MainTab";
import StopLossTab from "../../components/StopLossTab";
import TakeProfitTab from "../../components/TakeProfitTab";
import { TVChartContainer } from "binbot-charts";
import LogsInfo from "../../components/LogsInfo";
import {
  updateOrderLines,
  updateTimescaleMarks,
} from "../../components/services/charting.service.js";
class BotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      id: props.match.params.id ? props.match.params.id : null,
      activeTab: "main",
      toggleIndicators: true,
      currentChartPrice: 0,
      // Chart state
      soPriceDeviation: 0,
      currentOrderLines: [],
      interval: "1h", // Fix legacy candlestick_interval
    };
  }

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getSymbols();
    this.props.getEstimate();
    if (!checkValue(this.props.match.params.id)) {
      this.props.setBot({ formIsValid: true });
      this.props.getBot(this.props.match.params.id);
      this.computeAvailableBalance();
    } else {
      this.props.resetBot()
    }
    if (!checkValue(this.props.match.params?.symbol)) {
      this.props.setBot(
        {
          pair: this.props.match.params.symbol,
        },
        () => this.computeAvailableBalance()
      );
    }
  };

  componentDidUpdate = (p, s) => {
    if (p.symbolInfo !== this.props.symbolInfo) {
      this.computeAvailableBalance();
    }

    // If there is a newBotId, it means form was created
    // To make sure of this, check also URL has NO id param
    if (
      !checkValue(this.props.newBotId) &&
      this.props.newBotId !== p.newBotId &&
      checkValue(this.props.match.params.id)
    ) {
      this.props.history.push({
        pathname: `/admin/bots/edit/${this.props.newBotId}`,
      });
    }

    // Only for edit bot page
    // Fill up the candlestick when pair is available and inherit the interval too
    if (
      !checkValue(this.props.bot.pair) &&
      this.props.bot.pair !== p.bot.pair
    ) {
      getQuoteAsset(this.props.bot.pair).then(({ data }) =>
        this.props.setBot({ quoteAsset: data })
      );
      getBaseAsset(this.props.bot.pair).then(({ data }) =>
        this.props.setBot({ baseAsset: data })
      );
      const currentDate = moment().toISOString();
      this.props.setBot({
        name: `${this.props.bot.pair}_${currentDate}`,
      });

      this.marginShortValidation();
    }

    if (this.state.currentChartPrice !== s.currentChartPrice) {
      const newBotProfit = computeSingleBotProfit(
        this.props.bot,
        this.state.currentChartPrice
      );
      this.props.setBot({ bot_profit: newBotProfit });
    }

    if (
      this.props.bot.quoteAsset !== p.bot.quoteAsset &&
      !checkValue(this.props.balances)
    ) {
      this.computeAvailableBalance();
    }
  };

  marginShortValidation = async () => {
    return true
  };

  requiredinValidation = () => {
    const {
      pair,
      base_order_size,
      take_profit,
      trailling,
      trailling_deviation,
      stop_loss,
    } = this.props.bot;

    // If everything below is ok, form will be valid
    this.props.setBot({ formIsValid: true });

    if (checkValue(pair)) {
      this.props.setBot({ pairError: true, formIsValid: false });
      return false;
    } else {
      this.props.setBot({ pairError: false });
    }

    if (checkValue(base_order_size)) {
      this.props.setBot({ baseOrderSizeError: true, formIsValid: false });
      return false;
    } else {
      this.props.setBot({ baseOrderSizeError: false });
    }

    if (checkValue(take_profit) && checkBalance(take_profit)) {
      this.props.setBot({ takeProfitError: true, formIsValid: false });
      return false;
    } else {
      this.props.setBot({ takeProfitError: false });
    }

    if (!checkValue(stop_loss)) {
      if (parseFloat(stop_loss) > 100 || parseFloat(stop_loss) < 0) {
        this.props.setBot({ stopLossError: true, formIsValid: false });
      } else {
        this.props.setBot({ stopLossError: false });
      }
    }

    if (trailling === "true") {
      if (
        checkBalance(trailling_deviation) &&
        checkBalance(trailling_deviation)
      ) {
        this.props.setBot({
          traillingDeviationError: true,
          formIsValid: false,
        });
        return false;
      } else {
        this.props.setBot({ traillingDeviationError: false });
      }
    }

    this.marginShortValidation();

    return true;
  };

  computeAvailableBalance = () => {
    /**
     * Refer to bots.md
     */
    const { base_order_size } = this.props.bot;
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

      if (!checkValue(value) && !checkBalance(value) && this.props.bot) {
        const baseOrder = parseFloat(base_order_size) * 1; // base order * 100% of all balance
        const checkBaseOrder = this.props.bot.orders.find(
          (x) => x.deal_type === "base_order"
        );
        let updatedValue = value - baseOrder;
        if (!checkValue(checkBaseOrder) && "deal_type" in checkBaseOrder) {
          updatedValue = baseOrder + updatedValue;
        }
        updatedValue.toFixed(8);

        // Check that we have enough funds
        // If not return error
        if (parseFloat(updatedValue) > 0) {
          this.props.setBot({
            balance_available: updatedValue,
            balance_available_asset: name,
            baseOrderSizeError: false,
            balanceAvailableError: false,
          });
        } else {
          this.props.setBot({ baseOrderSizeError: true, formIsValid: false });
        }
      } else {
        this.props.setBot({
          balance_available: value,
          balance_available_asset: name,
          balanceAvailableError: true,
          formIsValid: false,
        });
      }
    }
  };

  handleSubmit = (e) => {
    e.preventDefault();
    const validation = this.requiredinValidation();
    if (validation) {
      const form = {
        status: this.props.bot.status,
        balance_to_use: this.props.bot.balance_to_use,
        base_order_size: String(this.props.bot.base_order_size),
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        safety_orders: this.props.bot.safety_orders,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
        stop_loss: this.props.bot.stop_loss,
        candlestick_interval: this.props.bot.candlestick_interval,
        cooldown: this.props.bot.cooldown,
        strategy: this.props.bot.strategy,
        short_buy_price: this.props.bot.short_buy_price,
        short_sell_price: this.props.bot.short_sell_price,
        margin_short_reversal: this.props.bot.margin_short_reversal,
        dynamic_trailling: this.props.bot.dynamic_trailling
      };
      if (this.state.id === null) {
        this.props.createBot(form);
      } else {
        this.props.editBot(this.state.id, form);
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
      this.props.setBot({ pair: value[0] });
    }
  };

  handleBaseChange = (e) => {
    this.props.setBot({ base_order_size: e.target.value });
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
      this.props.setBot({ base_order_size: minAmount });
    }
  };

  addAll = async () => {
    const { pair, quoteAsset } = this.props.bot;
    const { balance_raw: balances } = this.props;
    if (!checkValue(pair) && balances?.length > 0) {
      this.props.getSymbolInfo(pair);
      let totalBalance = 0;
      for (let x of balances) {
        if (x.asset === "GBP") {
          const rate = await convertGBP(quoteAsset + "GBP");
          if ("code" in rate.data) {
            this.props.setBot({
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
        this.props.setBot({ addAllError: "No balance available to add" });
      } else {
        this.props.setBot({ base_order_size: totalBalance });
      }
    }
  };

  handleSafety = (e) => {
    const { pair } = this.props.bot;
    this.props.getSymbolInfo(pair);
    this.props.setBot({ [e.target.name]: e.target.value });
  };

  handleChange = (e) => {
    e.preventDefault();
    this.props.setBot({ [e.target.name]: e.target.value });
  };

  handleBlur = (e) => {
    const { name, value } = e.target;
    if (name === "pair") {
      this.props.getSymbolInfo(value);
    }

    if (name === "strategy" && value === "margin_short") {
      this.marginShortValidation();
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

    this.computeAvailableBalance();
  };

  handleActivation = (e) => {
    const validation = this.requiredinValidation();
    if (validation) {
      this.handleSubmit(e);
      this.props.activateBot(this.state.id);
      this.props.getBot(this.props.match.params.id)
    }
  };

  toggleTrailling = (prop) => {
    const value = this.props.bot[prop] || this.props.bot[prop] === "true" ? false : true;
    this.props.setBot({
      [prop]: value,
    });
  }
    
  handleToggleIndicator = (value) => {
    this.setState({ toggleIndicators: value });
  };

  handleSoChange = (e) => {
    if (e.target.name === "so_size" || e.target.name === "buy_price") {
      const safety_orders = produce(this.props.bot, (draft) => {
        draft.safety_orders[e.target.dataset.index][e.target.name] =
          e.target.value;
      });
      this.props.setBot(safety_orders);
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
    this.props.setBot(safety_orders);
  };

  removeSo = (e) => {
    e.preventDefault();
    const safety_orders = produce(this.props.bot, (draft) => {
      draft.safety_orders.splice(e.target.dataset.index, 1);
    });
    this.props.setBot(safety_orders);
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

  toggleAutoswitch = value => {
    this.props.setBot({ margin_short_reversal: value })
  }

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
                      <Badge
                        color={
                          parseFloat(this.props.bot.bot_profit) > 0
                            ? "success"
                            : "danger"
                        }
                      >
                        {this.props.bot.bot_profit ?this.props.bot.bot_profit + "%" : "0%"}
                      </Badge>{" "}
                      {!checkValue(this.props.bot?.status) && (
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
                    {!checkValue(this.props.bot.bot_profit) &&
                      !isNaN(this.props.bot.bot_profit) && (
                        <h4>
                          Earnings after commissions (est.):{" "}
                          {roundDecimals(
                            parseFloat(this.props.bot.bot_profit) - 0.3
                          ) + "%"}
                        </h4>
                      )}
                  </Col>
                </Row>
              </CardHeader>
              <CardBody>
                {!checkValue(this.props.bot?.pair) && (
                  <TVChartContainer
                    symbol={this.props.bot.pair}
                    interval={this.state.interval}
                    timescaleMarks={updateTimescaleMarks(this.props.bot)}
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
          this.props.bot.orders?.length > 0 &&
          !checkValue(this.props.match.params.id) ? (
            <>
              <Col md="7" sm="12">
                <BotInfo bot={this.props.bot} />
              </Col>
              
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
                      baseOrderSizeInfoText="Must be filled in to calculate the other parameters. For short orders, this value must + stop_loss to cover losses"
                    />

                    {/*
                      Safey orders tab
                    */}
                    <SafetyOrdersTab
                      safetyOrders={this.props.bot.safety_orders}
                      asset={this.props.bot.pair}
                      quoteAsset={this.props.bot.quoteAsset}
                      soPriceDeviation={this.state.soPriceDeviation}
                      handleChange={this.handleSoChange}
                      addSo={this.addSo}
                      removeSo={this.removeSo}
                    />

                    <StopLossTab
                      stop_loss={this.props.bot.stop_loss}
                      stopLossError={this.props.bot.stopLossError}
                      margin_short_reversal={this.props.bot.margin_short_reversal}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                      toggleAutoswitch={this.toggleAutoswitch}
                    />

                    <TakeProfitTab
                      takeProfitError={this.props.bot.takeProfitError}
                      take_profit={this.props.bot.take_profit}
                      trailling={this.props.bot.trailling}
                      trailling_deviation={this.props.bot.trailling_deviation}
                      dynamic_trailling={this.props.bot.dynamic_trailling}
                      handleChange={this.handleChange}
                      handleBlur={this.handleBlur}
                      toggleTrailling={this.toggleTrailling}
                    />
                  </TabContent>
                  <Row xs="2">
                    <Col>
                      {this.props.bot.status !== "completed" && (
                        <ButtonToggle
                          className="btn-round"
                          color="primary"
                          onClick={this.handleActivation}
                          disabled={checkValue(this.props.bot.id)}
                        >
                          {this.props.bot.status === "active" &&
                          Object.keys(this.props.bot.deal).length > 0
                            ? "Update deal"
                            : "Deal"}
                        </ButtonToggle>
                      )}
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
                    <div>
                      <br />
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
                    </div>
                  )}
                </CardBody>
              </Card>
            </Col>
            <Col md="5" sm="12">
              {this.props.balance_estimate && (
                <BalanceAnalysis balance={this.props.balance_estimate} />
              )}
              {this.props.bot.errors?.length > 0 && (
                <LogsInfo events={this.props.bot.errors} />
              )}
            </Col>
          </Row>
        </Form>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: balance_raw } = state.balanceRawReducer;
  const { data: symbols } = state.symbolReducer;
  const { botId, botActive, bot } = state.botReducer;
  const { loading } = state.loadingReducer;
  const { data: balanceEstimate } = state.estimateReducer;

  return {
    balance_estimate: balanceEstimate,
    balance_raw: balance_raw,
    symbols: symbols,
    bot: bot,
    newBotId: botId,
    botActive: botActive,
    loading: loading,
  };
};

export default connect(mapStateToProps, {
  getEstimate,
  getBalanceRaw,
  getSymbols,
  getSymbolInfo,
  createBot,
  getBot,
  editBot,
  activateBot,
  deactivateBot,
  setBot,
  resetBot,
})(BotForm);
