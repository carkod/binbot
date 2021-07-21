import React from "react";
import "react-bootstrap-typeahead/css/Typeahead.css";
import { connect } from "react-redux";
import { Nav, NavItem, NavLink, TabContent, TabPane } from "reactstrap";
import { checkValue } from "../../validations";
import { loadCandlestick } from "../bots/actions";
import { getHistoricalResearchData, getResearchData } from "./actions";
import SignalsTab from "./SignalsTab";

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
      activeTab: "signalTab",
      candlestickSignalFilter: "positive",
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
    this.getData();
    this.pollData = setInterval(this.getData, this.state.poll_ms);
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notification");
    } else {
      Notification.requestPermission();
    }
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
    this.setState({ activeTab: "signalTab" }, () => {
      this.pollData = setInterval(this.getData, this.state.poll_ms);
    });
  };

  render() {
    return (
      <>
        <div className="content">
          <Nav tabs>
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
  return {
    research: research,
    candlestick: candlestick,
    historicalSignalReducer: historicalSignalReducer,
  };
};

export default connect(mapStateToProps, {
  getResearchData,
  loadCandlestick,
  getHistoricalResearchData,
})(Research);
