import produce from "immer";
import React from "react";
import "react-bootstrap-typeahead/css/Typeahead.css";
import { connect } from "react-redux";
import { Nav, NavItem, NavLink, TabContent, TabPane } from "reactstrap";
import { addNotification, checkValue } from "../../validations";
import { loadCandlestick, getSymbols } from "../bots/actions";
import { getBalanceRaw } from "../../state/balances/actions";
import {
  getHistoricalResearchData,
  getResearchData,
  getBlacklist,
  getSettings,
  editSettings,
  addBlackList,
  deleteBlackList,
} from "./actions";
import ControllerTab from "./ControllerTab";
import SignalsTab from "./SignalsTab";
import { gbpHedge } from "./requests";

class Research extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      candlestick_interval: "30m",
      order: false, // true = desc = -1, false = asc = 1
      order_by: "",
      strengthFilter: "ALL",
      sideFilter: "ALL",
      signal_notification: null,
      poll_ms: 10000,
      activeTab: "controllerTab",
      candlestickSignalFilter: "positive",
      settings: {},
      selectedBlacklist: "",
      balanceToUseUnmatchError: "",
    };
  }

  getData = () => {
    clearInterval(this.pollData);
    let filterBy,
      filter = null;
    if (this.state.sideFilter === "BUY" || this.state.sideFilter === "SELL") {
      filter = this.state.sideFilter;
      filterBy = "signal_side";
    }

    if (
      this.state.strengthFilter === "STRONG" ||
      this.state.strengthFilter === "WEAK"
    ) {
      filter = this.state.strengthFilter;
      filterBy = "signal_strength";
    }

    if (
      this.state.candlestickSignalFilter === "positive" ||
      this.state.candlestickSignalFilter === "negative"
    ) {
      filter = this.state.candlestickSignalFilter;
      filterBy = "candlestick_signal";
    }

    const params = {
      order_by: this.state.order_by,
      order: this.state.order,
      filter_by: filterBy,
      filter: filter,
    };
    if (
      (!checkValue(params.filter_by) && !checkValue(params.filter)) ||
      !checkValue(params.order_by)
    ) {
      this.props.getResearchData(params);
    } else {
      this.props.getResearchData();
    }
  };

  componentDidMount = () => {
    this.props.getSettings();
    this.props.getBlacklist();
    this.props.getSymbols();
    this.props.getBalanceRaw();
  };

  componentDidUpdate = (p, s) => {
    // Candlestick data updates
    if (!checkValue(this.props.pair) && this.props.pair !== p.pair) {
      this.setState({ pair: this.props.pair });
      this.props.loadCandlestick(
        this.props.pair,
        this.state.candlestick_interval
      );
    }

    if (
      !checkValue(this.state.pair) &&
      !checkValue(this.state.candlestick_interval) &&
      this.state.candlestick_interval !== s.candlestick_interval
    ) {
      this.props.loadCandlestick(
        this.state.pair,
        this.state.candlestick_interval
      );
    }

    if (
      !checkValue(this.props.research) &&
      this.props.research !== p.research
    ) {
      let strongest = [];
      this.props.research.forEach((element) => {
        if (element.signal_strength === "STRONG") {
          const strongBuy = {
            pair: element.market,
            spread: element.spread,
          };
          strongest.push(strongBuy);
        }
      });
      if (strongest.length > 0) {
        const maxSpread = Math.max.apply(
          Math,
          strongest.map((element) => element.spread)
        );
        const maxPair = strongest.find((x) => x.spread === maxSpread);
        if (maxPair.pair !== this.state.signal_notification) {
          this.setState({ signal_notification: maxPair.pair });
          this.showNotification(`STRONG BUY signal for ${maxPair.pair}`);
        }
      }
    }

    if (p.settings !== this.props.settings) {
      this.setState({ settings: this.props.settings });
    }
    if (p.blacklistData !== this.props.blacklistData) {
      this.setState({ blacklistData: this.props.blacklistData });
    }

    if (p.balance_raw !== this.props.balance_raw) {
      this.handleBalanceToUseBlur();
    }
  };

  componentWillUnmount = () => {
    clearInterval(this.pollData);
  };

  handleSetPair = (pair) => {
    this.props.loadCandlestick(pair, this.state.candlestick_interval);
    this.setState({ pair: pair });
  };

  handleInterval = (e) => {
    e.preventDefault();
    if (!checkValue(this.state.pair)) {
      this.props.loadCandlestick(this.state.pair, e.target.value);
    }
    this.setState({ candlestick_interval: e.target.value });
  };

  showNotification = (message) => {
    new Notification(message);
  };

  handleSignalsOrder = (type) => {
    const { order } = this.state;
    this.setState({ order: !order, order_by: type }, () => {
      this.pollData = setInterval(this.getData, this.state.poll_ms);
    });
  };

  handleSignalsFilter = (e) => {
    this.setState({ [e.target.name]: e.target.value }, () => {
      this.pollData = setInterval(this.getData, this.state.poll_ms);
    });
  };

  toggleSignalTab = () => {
    this.getData();
    this.pollData = setInterval(this.getData, this.state.poll_ms);
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notification");
    } else {
      Notification.requestPermission();
    }
    this.setState({ activeTab: "signalTab" });
  };

  handleSettings = (e) => {
    e.preventDefault();
    this.setState(
      produce((draft) => {
        draft.settings[e.target.name] = e.target.value;
      })
    );
  };

  saveSettings = (e) => {
    e.preventDefault();
    this.setState(
      produce((draft) => {
        draft.settings.update_required = "true";
      }), () => this.props.editSettings(this.state.settings)
    );
  };


  handleBlacklist = (action, data) => {
    if (action === "add") {
      this.props.addBlackList(data);
    }
    if (action === "delete") {
      this.props.deleteBlackList(data);
    }
    this.props.getBlacklist();
  };

  toggleTrailling = () => {
    if (this.state.settings.trailling === "true") {
      this.setState(
        produce((draft) => {
          draft.settings.trailling = "false"
        })
      );
    } else {
      this.setState(
        produce((draft) => {
          draft.settings.trailling = "true"
        })
      );
    }
  }

  handleBalanceToUseBlur = () => {
    const searchBalance = this.props.balance_raw.findIndex(b => b["asset"] === this.state.settings.balance_to_use);
    if (searchBalance === -1) {
      this.setState({
        balanceToUseUnmatchError: "Balance to use does not match available balance. Autotrade will fail."
      });
    } else {
      this.setState({
        balanceToUseUnmatchError: ""
      });
    }
  }

  triggerGbpHedge = async (asset) => {
    console.log(asset);
    const res = gbpHedge(asset);
    if (res.error === 1) {
      addNotification("Some errors encountered", res.message, "error");
    } else {
      addNotification("SUCCESS!", res.message, "success");
    }
  }

  render() {
    return (
      <>
        <div className="content">
          <Nav tabs>
            <NavItem>
              <NavLink
                className={
                  this.state.activeTab === "controllerTab" ? "active" : ""
                }
                onClick={() => this.setState({ activeTab: "controllerTab" })}
              >
                Controller
              </NavLink>
            </NavItem>
            <NavItem>
              <NavLink
                className={this.state.activeTab === "signalTab" ? "active" : ""}
                onClick={this.toggleSignalTab}
              >
                Signals
              </NavLink>
            </NavItem>
          </Nav>
          <TabContent activeTab={this.state.activeTab}>
            <TabPane tabId="controllerTab">
              <ControllerTab
                blacklistData={this.state.blacklistData}
                symbols={this.props.symbols}
                settings={this.state.settings}
                handleInput={this.handleSettings}
                handleBlacklist={this.handleBlacklist}
                saveSettings={this.saveSettings}
                toggleTrailling={this.toggleTrailling}
                balanceToUseUnmatchError={this.state.balanceToUseUnmatchError}
                handleBalanceToUseBlur={this.handleBalanceToUseBlur}
                triggerGbpHedge={this.triggerGbpHedge}
              />
            </TabPane>
            <TabPane tabId="signalTab">
              <SignalsTab
                candlestick={this.props.candlestick}
                pair={this.state.pair}
                candlestick_interval={this.state.candlestick_interval}
                strengthFilter={this.state.strengthFilter}
                research={this.props.research}
                sideFilter={this.state.sideFilter}
                candlestickSignalFilter={this.state.candlestickSignalFilter}
                handleInterval={this.handleInterval}
                handleSignalsFilter={this.handleSignalsFilter}
                handleSetPair={this.handleSetPair}
                handleSignalsOrder={this.handleSignalsOrder}
              />
            </TabPane>
          </TabContent>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: research } = state.researchReducer;
  const { data: candlestick } = state.candlestickReducer;
  const { data: historicalSignalReducer } = state.historicalResearchReducer;
  const { data: symbols } = state.symbolReducer;
  const { data: blacklistData } = state.blacklistReducer;
  const { data: settings } = state.settingsReducer;
  const { data: balance_raw } = state.balanceRawReducer;

  return {
    research: research,
    candlestick: candlestick,
    historicalSignalReducer: historicalSignalReducer,
    symbols: symbols,
    blacklistData: blacklistData,
    settings: settings,
    balance_raw: balance_raw,
  };
};

export default connect(mapStateToProps, {
  getResearchData,
  loadCandlestick,
  getHistoricalResearchData,
  getSymbols,
  getBlacklist,
  addBlackList,
  deleteBlackList,
  getSettings,
  editSettings,
  getBalanceRaw,
})(Research);
