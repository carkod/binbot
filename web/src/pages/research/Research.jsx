import React from "react";
import { connect } from "react-redux";
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Row,
} from "reactstrap";
import Candlestick from "../../components/Candlestick";
import { checkValue, intervalOptions } from "../../validations";
import { loadCandlestick } from "../bots/actions";
import { getResearchData } from "./actions";
import Signals from "./Signals";

class Research extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      activeTab: "signals",
      candlestick_interval: "1h",
    };
  }

  componentDidMount = () => {
    this.props.getResearchData();
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

    if (!checkValue(this.state.pair) && !checkValue(this.state.candlestick_interval) && this.state.candlestick_interval !== s.candlestick_interval) {
      this.props.loadCandlestick(
        this.state.pair,
        this.state.candlestick_interval
      );
    }
  };

  handleSetPair = (pair) => {
    this.props.loadCandlestick(pair, this.state.candlestick_interval);
    this.setState({ pair: pair });
  };

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
                      1 minute interval only. Signals update with websockets every 1 minute.
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
            <Col md="6" sm="3">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <h2>Signals</h2>
                    <small>1 minute</small>
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  {this.props.research && this.props.research.length > 0 ? (
                    <Signals
                      data={this.props.research}
                      setPair={this.handleSetPair}
                    />
                  ) : (
                    "No signals available"
                  )}
                </CardBody>
              </Card>
            </Col>
            <Col md="6" sm="7">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <h2>Correlations</h2>
                  </CardTitle>
                </CardHeader>
                <CardBody>Correlations content</CardBody>
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
