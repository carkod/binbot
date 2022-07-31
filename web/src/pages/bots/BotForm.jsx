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
import IndicatorsButtons from "../../components/IndicatorsButtons";
import { getBalance, getBalanceRaw } from "../../state/balances/actions";
import { bot } from "../../state/bots/actions";
import {
  checkBalance,
  checkValue,
  intervalOptions,
  roundDecimals,
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
  setBot,
} from "./actions";
import { convertGBP, getQuoteAsset } from "./requests";
import MainTab from "./tabs/Main";
import StopLoss from "./tabs/StopLoss";
import TakeProfit from "./tabs/TakeProfit";

class BotForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      _id: props.match.params.id ? props.match.params.id : null,
      bot_profit: 0,
      activeTab: "main",
      toggleIndicators: true,
    };
  }

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getBalance();
    this.props.getSymbols();
    if (!checkValue(this.props.match.params.id)) {
      this.props.setBot({ formIsValid: true });
      this.props.getBot(this.props.match.params.id);
      this.computeAvailableBalance();
    }
    if (!checkValue(this.props.match.params?.symbol)) {
      this.props.setBot(
        {
          pair: this.props.match.params.symbol,
        },
        () => this.computeAvailableBalance()
      );
    }
    if (checkValue(this.props.match.params.symbol)) {
      this.props.setBot(bot);
    }
  };

  componentDidUpdate = (p, s) => {
    if (p.symbolInfo !== this.props.symbolInfo) {
      this.computeAvailableBalance();
    }

    if (
      !checkValue(this.props.bot.pair) &&
      p.bot.candlestick_interval !== this.props.bot.candlestick_interval
    ) {
      this.props.loadCandlestick(
        this.props.bot.pair,
        this.props.bot.candlestick_interval,
        this.props.bot?.deal?.buy_timestamp
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
        pathname: `/admin/bots/edit/${this.props.newBotId}`,
        state: { candlestick_interval: this.props.bot.candlestick_interval },
      });
    }

    // Only for edit bot page
    // Fill up the candlestick when pair is available and inherit the interval too
    if (
      !checkValue(this.props.bot.pair) &&
      this.props.bot.pair !== p.bot.pair
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
        this.props.setBot({ quoteAsset: data })
      );
      const currentDate = moment().toISOString();
      this.props.setBot({
        name: `${this.props.bot.pair}_${currentDate}`,
      });
    }

    // Candlestick data updates
    if (
      !checkValue(this.props.candlestick) &&
      this.props.candlestick !== p.candlestick &&
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
    }

    if (
      this.props.bot.quoteAsset !== p.bot.quoteAsset &&
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

    if (checkValue(max_so_count)) {
      if (checkBalance(so_size) && checkBalance(so_size)) {
        this.props.setBot({ soSizeError: true, formIsValid: false });
        return false;
      } else {
        this.props.setBot({ soSizeError: false });
      }
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
        max_so_count: this.props.bot.max_so_count,
        name: this.props.bot.name,
        pair: this.props.bot.pair,
        take_profit: this.props.bot.take_profit,
        trailling: this.props.bot.trailling,
        trailling_deviation: this.props.bot.trailling_deviation,
        stop_loss: this.props.bot.stop_loss,
        candlestick_interval: this.props.bot.candlestick_interval,
        cooldown: this.props.bot.cooldown
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
      this.computeAvailableBalance();
    }
  };

  handleActivation = async (e) => {
    const validation = this.requiredinValidation();
    if (validation) {
      await this.handleSubmit(e);
      this.props.activateBot(this.state._id);
    }
  };

  handleMaxSoChange = (e) => {
    e.preventDefault();
    const count = parseInt(this.props.bot.max_so_count);
    const value = parseInt(e.target.value);
    if (count !== value) {
      this.props.setBot({ [e.target.name]: e.target.value }, () =>
        this.renderSO()
      );
    }
  };

  toggleTrailling = () =>
    this.props.setBot({
      trailling: this.state.trailling === "true" ? "false" : "true",
    });

  handleToggleIndicator = (value) => {
    this.setState({ toggleIndicators: value });
  };

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
                        )}{" "}
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
                      )}
                    </CardTitle>
                  </Col>
                  <Col>
                    {!checkValue(this.state.bot_profit) &&
                      !isNaN(this.state.bot_profit) && (
                        <h4>
                          Earnings after commissions (est.):{" "}
                          {roundDecimals(
                            parseFloat(this.state.bot_profit) - 0.3
                          ) + "%"}
                        </h4>
                      )}
                  </Col>
                </Row>
                <br />
                <Row>
                  <Col>
                    {intervalOptions.map((item) => (
                      <Badge
                        key={item}
                        onClick={() =>
                          this.props.setBot({ candlestick_interval: item })
                        }
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
                {this.props.candlestick &&
                this.props.candlestick.error !== 1 &&
                !checkValue(this.props.bot.pair) ? (
                  <Candlestick
                    data={this.props.candlestick}
                    bot={this.props.bot}
                    deal={
                      this.props.bot && this.props.bot.deal
                        ? this.props.bot.deal
                        : null
                    }
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
          this.props.bot.orders?.length > 0 &&
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
                            invalid={this.props.bot.maxSOCountError}
                            type="text"
                            name="max_so_count"
                            onChange={this.handleMaxSoChange}
                            onBlur={this.handleBlur}
                            value={this.props.bot.max_so_count}
                          />
                          <FormFeedback>
                            <strong>Safety order size</strong> is required.
                          </FormFeedback>
                          <small>
                            If value = 0, Safety orders will be turned off
                          </small>
                        </Col>
                      </Row>
                    </TabPane>

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
                        disabled={checkValue(this.props.bot._id)}
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
              {this.props.lastBalance && this.props.balance_raw && (
                <BalanceAnalysis
                  balance={this.props.lastBalance}
                  balance_raw={this.props.balance_raw}
                />
              )}
            </Col>
          </Row>
        </Form>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  let { data: balance } = state.balanceReducer;
  const { data: balance_raw } = state.balanceRawReducer;
  const { data: symbols } = state.symbolReducer;
  const { data: candlestick } = state.candlestickReducer;
  const { botId, botActive, bot } = state.botReducer;
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
  setBot,
})(BotForm);
