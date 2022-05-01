import produce from "immer";
import React from "react";
import "react-bootstrap-typeahead/css/Typeahead.css";
import { connect } from "react-redux";
import { Nav, NavItem, NavLink, TabContent, TabPane } from "reactstrap";
import { addNotification, checkValue } from "../../validations";
import { loadCandlestick, getSymbols } from "../bots/actions";
import { getBalanceRaw } from "../../state/balances/actions";
import {
  getBlacklist,
  getSettings,
  editSettings,
  addBlackList,
  deleteBlackList,
  setSettingsState
} from "./actions";
import ControllerTab from "./ControllerTab";
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
      activeTab: "controllerTab",
      candlestickSignalFilter: "positive",
      settings: {},
      selectedBlacklist: "",
      balanceToUseUnmatchError: "",
      minBalanceSizeToUseError: ""
    };
  }

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

    if (p.blacklistData !== this.props.blacklistData) {
      this.setState({ blacklistData: this.props.blacklistData });
    }

    if (p.balance_raw !== this.props.balance_raw) {
      this.handleBalanceToUseBlur();
    }
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

  handleSettings = (e) => {
    e.preventDefault();
    this.props.setSettingsState({
      [e.target.name]: e.target.value
    })
  };

  saveSettings = (e) => {
    e.preventDefault();
    this.props.setSettingsState({
      update_required: "true"
    });
    this.props.editSettings(this.props.settings)
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
    if (this.props.settings.trailling === "true") {
      this.props.setSettingsState({
        trailling: "false"
      });
    } else {
      this.props.setSettingsState({
        trailling: "true"
      });
    }
  }

  handleBalanceToUseBlur = () => {
    const searchBalance = this.props.balance_raw.findIndex(b => b["asset"] === this.props.settings.balance_to_use);
    if (searchBalance === -1) {
      this.setState({
        balanceToUseUnmatchError: "Balance to use does not match available balance. Autotrade will fail."
      });
    } else {
      this.setState(
        produce((draft) => {
          draft.balanceToUseUnmatchError = ""
        })
      );
    }
  }

  handleBalanceSizeToUseBlur = () => {
    const searchBalance = this.props.balance_raw.find(b => b["asset"] === this.props.settings.balance_to_use);
    if (parseFloat(searchBalance.free) < parseFloat(this.props.settings.balance_size_to_use)) {
      this.setState({
        minBalanceSizeToUseError: "Not enough balance for bot base orders"
      });
    } else {
      this.setState({
        minBalanceSizeToUseError: ""
      });
    }
  }

  triggerGbpHedge = async (asset) => {
    const res = gbpHedge(asset);
    if (res.error === 1) {
      addNotification("Some errors encountered", res.message, "error");
    } else {
      addNotification("SUCCESS!", res.message, "success");
    }
  }

  addCurrentBalance = () => {
    const searchBalance = this.props.balance_raw.find(b => b.asset === this.props.settings.balance_to_use);
    this.props.setSettingsState({
      balance_size_to_use: searchBalance.free
    })
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
          </Nav>
          <TabContent activeTab={this.state.activeTab}>
            <TabPane tabId="controllerTab">
              { this.props.settings && <ControllerTab
                blacklistData={this.state.blacklistData}
                symbols={this.props.symbols}
                settings={this.props.settings}
                handleInput={this.handleSettings}
                handleBlacklist={this.handleBlacklist}
                saveSettings={this.saveSettings}
                toggleTrailling={this.toggleTrailling}
                balanceToUseUnmatchError={this.state.balanceToUseUnmatchError}
                handleBalanceToUseBlur={this.handleBalanceToUseBlur}
                triggerGbpHedge={this.triggerGbpHedge}
                handleBalanceSizeToUseBlur={this.handleBalanceSizeToUseBlur}
                minBalanceSizeToUseError={this.state.minBalanceSizeToUseError}
                allBalance={() => this.setState(
                  produce((draft) => {
                    draft.settings.balance_size_to_use = 0;
                  })
                )}
                addAll={this.addCurrentBalance}
              /> }
            </TabPane>
          </TabContent>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: candlestick } = state.candlestickReducer;
  const { data: symbols } = state.symbolReducer;
  const { data: blacklistData } = state.blacklistReducer;
  const { settings } = state.settingsReducer;
  const { data: balance_raw } = state.balanceRawReducer;

  return {
    candlestick: candlestick,
    symbols: symbols,
    blacklistData: blacklistData,
    settings: settings,
    balance_raw: balance_raw,
  };
};

export default connect(mapStateToProps, {
  loadCandlestick,
  getSymbols,
  getBlacklist,
  addBlackList,
  deleteBlackList,
  getSettings,
  editSettings,
  getBalanceRaw,
  setSettingsState
})(Research);
