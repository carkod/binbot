import React from "react";
import { connect } from "react-redux";
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  CardTitle,
  Col,
  Row,
} from "reactstrap";
import LineChart from "../../components/LineChart";

import { checkValue, listCssColors } from "../../validations";
import { getAssets, getBalanceInBtc, getBalanceDiff } from "./actions";
import { AssetsPie } from "./AssetsPie";
import { NetWorthChart } from "./NetWorthChart";
import { PortfolioBenchmarkChart } from "./PortfolioBenchmarkChart";
import { roundDecimals } from "../../validations";

class Dashboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      revenue: 0,
      percentageRevenue: "0",
      lineChartData: null,
      lineChartLegend: null,
      pieChartData: null,
      pieChartLegend: null,
      netWorth: null,
      netWorthLegend: null,
      networthLayout: null,
    };
  }

  componentDidMount = () => {
    this.props.getBalanceInBtc();
    this.props.getAssets();
    this.props.getBalanceDiff("7");
  };

  componentDidUpdate = (p, s) => {
    if (
      !checkValue(this.props.balances) &&
      p.balances !== this.props.balances &&
      !checkValue(this.props.totalBtcBalance) &&
      p.totalBtcBalance !== this.props.totalBtcBalance
    ) {
      this.computePieChart(this.props.balances, this.props.totalBtcBalance);
    }
    if (
      !checkValue(this.props.balanceDiff) &&
      p.balanceDiff !== this.props.balanceDiff
    ) {
      this.computeDiffAssets(this.props.balanceDiff);
      this.netWorth(this.props.balanceDiff);
    }

    if (
      !checkValue(this.props.btcChange) &&
      p.btcChange !== this.props.btcChange
    ) {
      this.computeLineChart(this.props.assets, this.props.btcChange);
    }
  };

  computeDiffAssets = (assets) => {
    const balances = assets.reverse();
    const yesterday = balances[0].estimated_total_usd * balances[0].estimated_total_btc;
    const previousYesterday = balances[1].estimated_total_usd * balances[1].estimated_total_btc;
    const diff = yesterday - previousYesterday;
    const revenue = roundDecimals(diff, 4);
    const percentage = roundDecimals(diff / previousYesterday, 4) * 100
    
    this.setState({ revenue: revenue, percentageRevenue: percentage });
  };

  computeLineChart = (assets, btcChange) => {
    /**
     * Compute percentage increases benchmark
     * BTC vs Portfolio
     *
     */
    const dates = [];
    const values = [];
    assets.forEach((a, i) => {
      const b = assets[i + 1];
      if (b !== undefined) {
        const date = new Date(b.updatedTime * 1000);
        const value =
          [(a.total_btc_value - b.total_btc_value) / a.total_btc_value] * 100;
        dates.push(date);
        values.push(value);
      }
    });
    const trace = {
      x: dates,
      y: values,
      type: "scatter",
      mode: "lines+markers",
      connectgaps: true,
      line: {
        color: listCssColors[0],
        width: 1,
      },
      marker: {
        color: listCssColors[0],
        size: 8,
      },
    };
    const assetsLegend = {
      name: "Portfolio",
      color: listCssColors[0],
    };

    // Trace 2
    btcChange.line = {
      color: listCssColors[1],
      width: 1,
    };
    btcChange.marker = {
      color: listCssColors[1],
      size: 8,
    };
    const btcChangeLegend = {
      name: "BTC on USDT",
      color: listCssColors[1],
    };
    this.setState({
      lineChartData: [trace, btcChange],
      lineChartLegend: [assetsLegend, btcChangeLegend],
    });
  };

  computePieChart = (assets, total) => {
    let values = [];
    let labels = [];
    let pieChartLegend = [];
    assets.forEach((x, i) => {
      const percent = (x.btc_value / total).toFixed(4);
      values.push(percent);
      labels.push(x.asset);
      pieChartLegend.push({
        name: x.asset,
        color: listCssColors[i],
      });
    });
    const data = [
      {
        values: values,
        labels: labels,
        type: "pie",
        marker: {
          colors: listCssColors,
        },
      },
    ];
    this.setState({ pieChartData: data, pieChartLegend: pieChartLegend });
  };

  netWorth = (data) => {
    let dates = [];
    let values = [];
    if (!checkValue(data)) {
      data.forEach((a, i) => {
        dates.push(a.time);
        values.push(Math.floor(a.estimated_total_usd * a.estimated_total_btc));
      });
    }
    const trace = {
      x: dates,
      y: values,
      type: "scatter",
      mode: "lines+markers",
      connectgaps: true,
      line: {
        color: listCssColors[0],
        width: 1,
      },
      marker: {
        color: listCssColors[0],
        size: 8,
      },
    };

    this.setState({ netWorth: [trace] });
  };

  render() {
    const { balances, assets } = this.props;
    return (
      <>
        <div className="content">
          <Row>
            <Col lg="4" md="6" sm="6">
              <Card className="card-stats">
                <CardBody>
                  <Row>
                    <Col md="8" xs="12">
                      <div className="stats">
                        <p className="card-category">Balance</p>
                        {balances &&
                          balances.map((x, i) => (
                            <CardTitle
                              key={i}
                              tag="h5"
                              className={`card-title`}
                            >
                              <span
                                className={
                                  Math.max.apply(
                                    Math,
                                    balances.map((o) => o.total_btc_value)
                                  ) === x.free
                                    ? "u-green-badge"
                                    : ""
                                }
                              >
                                {x.free}
                              </span>
                            </CardTitle>
                          ))}
                      </div>
                    </Col>
                    <Col md="4" xs="12">
                      <div className="stats">
                        <p className="card-category">Asset</p>
                        {balances &&
                          balances.map((x, i) => (
                            <CardTitle key={i} tag="h5" className="card-title">
                              {x.asset}
                            </CardTitle>
                          ))}
                      </div>
                    </Col>
                  </Row>
                </CardBody>
                <CardFooter>
                  <hr />
                  <div className="stats">
                    {assets &&
                      `Total ${parseFloat(assets[0].total_btc_value).toFixed(
                        6
                      )} BTC`}
                  </div>
                </CardFooter>
              </Card>
            </Col>
            <Col lg="4" md="6" sm="6">
              <Card className="card-stats">
                <CardBody>
                  <Row>
                    <Col md="4" xs="5">
                      <div className="icon-big text-center icon-warning">
                        <i className="nc-icon nc-money-coins text-success" />
                      </div>
                    </Col>
                    <Col md="8" xs="7">
                      <div className="numbers">
                        <p className="card-category">P&L</p>
                        <CardTitle
                          tag="p"
                          className={
                            this.state.revenue > 0
                              ? "text-success"
                              : "text-danger"
                          }
                        >
                          <p>{this.state.percentageRevenue &&
                            `${this.state.percentageRevenue}%`}
                          </p>
                          <p>
                          {this.state.revenue &&
                            `$${this.state.revenue}`}
                          </p>
                        </CardTitle>
                        <p />
                      </div>
                    </Col>
                  </Row>
                </CardBody>
                <CardFooter>
                  <hr />
                  <i className="fas fa-sync" /> Yesterday
                </CardFooter>
              </Card>
            </Col>
            <Col lg="4" md="6" sm="6">
              <Card className="card-stats">
                <CardBody>
                  <Row>
                    <Col md="4" xs="5">
                      <div className="icon-big text-center icon-warning">
                        <i className="nc-icon nc-vector text-danger" />
                      </div>
                    </Col>
                    <Col md="8" xs="7">
                      <div className="numbers">
                        <p className="card-category">Errors</p>
                        <CardTitle tag="p">23</CardTitle>
                        <p />
                      </div>
                    </Col>
                  </Row>
                </CardBody>
                <CardFooter>
                  <hr />
                  <div className="stats">
                    <i className="far fa-clock" /> In the last hour
                  </div>
                </CardFooter>
              </Card>
            </Col>
          </Row>
          <Row>
            <Col md="4">
              <AssetsPie
                data={this.state.pieChartData}
                legend={this.state.pieChartLegend}
              />
            </Col>
            <Col md="8">
              { this.state.lineChartData && 
                <PortfolioBenchmarkChart
                  data={this.state.lineChartData}
                  legend={this.state.lineChartLegend}
                />
              }
            </Col>
          </Row>
          <Row>
            <Col md="4">
              {this.state.netWorth && (
                <NetWorthChart data={this.state.netWorth} />
              )}
            </Col>
            <Col md="8">
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (s) => {
  const { data: account } = s.balanceInBtcReducer;
  const { data: assets } = s.assetsReducer;
  const { data: balanceDiff } = s.balanceDiffReducer;
  let props = {
    balances: !checkValue(account) ? account.balances : null,
    totalBtcBalance: !checkValue(account) ? account.total_btc : null,
    assets: assets,
    balanceDiff: balanceDiff,
  };
  return props;
};

export default connect(mapStateToProps, {
  getBalanceInBtc,
  getAssets,
  getBalanceDiff,
})(Dashboard);
