import React from "react";
import "react-bootstrap-typeahead/css/Typeahead.css";
import { connect } from "react-redux";
import { Nav, NavItem, NavLink, TabContent, TabPane } from "reactstrap";
import { addNotification, checkValue } from "../../validations";
import { loadCandlestick, getSymbols } from "../bots/actions";
import { getBalanceRaw } from "../../state/balances/actions";
import {
  getBlacklist,
  addBlackList,
  deleteBlackList,
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
      selectedBlacklist: "",
      balanceToUseUnmatchError: "",
      minBalanceSizeToUseError: ""
    };
  }

  componentDidMount = () => {
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

  triggerGbpHedge = async (asset) => {
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
          </Nav>
          <TabContent activeTab={this.state.activeTab}>
            <TabPane tabId="controllerTab">
              <ControllerTab
                blacklistData={this.state.blacklistData}
                symbols={this.props.symbols}
                addToBlacklist={(data) => this.props.addBlackList(data)}
                removeFromBlacklist={(data) => this.props.deleteBlackList(data)}
                triggerGbpHedge={this.triggerGbpHedge}
              /> 
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
  const { data: balanceRaw } = state.balanceRawReducer;

  return {
    candlestick: candlestick,
    symbols: symbols,
    blacklistData: blacklistData,
    balance_raw: balanceRaw,
  };
};

export default connect(mapStateToProps, {
  loadCandlestick,
  getSymbols,
  getBlacklist,
  addBlackList,
  deleteBlackList,
  getBalanceRaw
})(Research);
