import React from "react";
import "react-bootstrap-typeahead/css/Typeahead.css";
import { connect } from "react-redux";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  FormGroup,
  Label,
  Input,
  Row,
} from "reactstrap";
import Candlestick from "../../components/Candlestick";
import { checkValue, intervalOptions } from "../../validations";
import { loadCandlestick } from "../bots/actions";
import { getResearchData } from "./actions";
import Signals from "./Signals";


const filterOptions = ["", "BUY", "SELL", "STRONG", "WEAK"];

class Research extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      candlestick_interval: "30m",
      order: false, // true = desc = -1, false = asc = 1
      filter: "",
      signal_notification: null,
      poll_ms: 10000,
    };
  }

  getData = () => {
    let filterBy, filter;
    if (this.state.filter === "BUY" || this.state.filter === "SELL") {
      filter = this.state.filter;
      filterBy = "signal_side";
    }

    if (this.state.filter === "STRONG" || this.state.filter === "WEAK") {
      filter = this.state.filter;
      filterBy = "signal_strength";
    }

    this.setState({ filter: this.state.filter, filter_by: filterBy });

    const params = {
      filter_by: filterBy,
      filter: filter,
    }
    this.props.getResearchData(params)
  }

  componentDidMount = () => {
    this.props.getResearchData();
    this.pollData = setInterval(() => this.getData(this.state.filter), this.state.poll_ms)
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

    if (!checkValue(this.props.research) && this.props.research !== p.research) {
      let strongest = [];
      this.props.research.forEach(element => {
        if (element.signal_strength === "STRONG") {
          const strongBuy = {
            pair: element.market_a,
            spread: element.spread
          }
          strongest.push(strongBuy);
        }
      });
      if (strongest.length > 0) {
        const maxSpread = Math.max.apply(Math, strongest.map((element) => element.spread))
        const maxPair = strongest.find(x => x.spread === maxSpread);
        if (maxPair.pair !== this.state.signal_notification) {
          this.setState({ signal_notification: maxPair.pair });
          this.showNotification(`STRONG BUY signal for ${maxPair.pair}`)
        }
      }
    }
  };

  componentWillUnmount = () => {
    this.pollData = null;
  }

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

  showNotification(message) {
    new Notification(message)
  }

  handleSignalsOrder = (type) => {
    const { order, filter_by, filter} = this.state;
    const params = {
      order_by: type,
      order: order ? 1 : -1,
      filter_by: filter_by,
      filter: filter,
    }
    this.setState({ order: !order })
    this.props.getResearchData(params);
  }

  handleSignalsFilter = (e) => {
    this.setState({ filter: e.target.value }, () => {
      this.pollData = null;
      this.getData(e.target.value);
      this.pollData = setInterval(() => this.getData(), this.state.poll_ms);
    });
    
  }

  render() {
    return (
      <>
        <div className="content">
          {this.state.pair && (
            <Row>
              <Col md="12">
                <Card style={{ minHeight: "650px" }}>
                  <CardHeader>
                    <CardTitle tag="h3">{this.state.pair}</CardTitle>
                    Interval: {this.state.candlestick_interval}
                  </CardHeader>
                  <CardBody>
                    {this.props.candlestick && !checkValue(this.state.pair) ? (
                      <Candlestick data={this.props.candlestick} />
                    ) : (
                      ""
                    )}
                  </CardBody>
                </Card>
              </Col>
            </Row>
          )}
          <Row>
            <Col md="12" sm="3">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <h2>Signals</h2>
                    <Row>
                      <Col md="6">
                        <FormGroup>
                          <Label for="candlestick_interval">Select Interval</Label>
                          <Input
                            type="select"
                            name="candlestick_interval"
                            id="interval"
                            onChange={this.handleInterval}
                            defaultValue={this.state.candlestick_interval}
                          >
                            {intervalOptions.map((x, i) => (
                              <option key={x} value={x}>
                                {x}
                              </option>
                            ))}
                          </Input>
                        </FormGroup>
                      </Col>
                      <Col md="6">
                        <FormGroup>
                          <Label for="activeFilter">Filter by:</Label>
                          <Input
                            type="select"
                            name="activeFilter"
                            id="filter-by"
                            onChange={this.handleSignalsFilter}
                            defaultValue={this.state.activeFilter}
                          >
                            {filterOptions.map((x, i) => (
                              <option key={i} value={x}>
                                {x}
                              </option>
                            ))}
                          </Input>
                        </FormGroup>
                      </Col>
                    </Row>
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  {this.props.research && this.props.research.length > 0 ? (
                    <Signals
                      data={this.props.research}
                      setPair={this.handleSetPair}
                      orderBy={this.handleSignalsOrder}
                    />
                  ) : (
                    "No signals available"
                  )}
                </CardBody>
              </Card>
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: research } = state.researchReducer;
  const { data: candlestick } = state.candlestickReducer;
  return {
    research: research,
    candlestick: candlestick,
  };
};

export default connect(mapStateToProps, { getResearchData, loadCandlestick })(
  Research
);
