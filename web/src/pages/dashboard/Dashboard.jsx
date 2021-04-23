import React from "react";
import { connect } from "react-redux";
import { Card, CardBody, CardFooter, CardTitle, Col, Row } from "reactstrap";
import { checkValue, listCssColors, roundDecimals } from "../../validations";
import { getAssets, getBalanceDiff, getBalanceInBtc } from "./actions";
import { AssetsPie } from "./AssetsPie";
import { NetWorthChart } from "./NetWorthChart";
import { PortfolioBenchmarkChart } from "./PortfolioBenchmarkChart";
import { ProfitLossBars } from "./ProfitLossBars";
import request from "../../request";
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
      dailyPnL: null,
      usdBalance: 0, // Does not rely on cronjob totalBtcBalance
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
      this.computeUsdBalance(this.props.balances);
    }
    if (
      !checkValue(this.props.balanceDiff) &&
      p.balanceDiff !== this.props.balanceDiff
    ) {
      this.computeDiffAssets(this.props.balanceDiff);
      this.computeNetWorth(this.props.balanceDiff);
      this.computeLineChart(this.props.balanceDiff);
      this.computeDailyPnL(this.props.balanceDiff);
    }
  };

  computeDiffAssets = (assets) => {
    const balances = assets.reverse();
    let revenue,
      percentage = "N/A";
    if (balances.length > 0) {
      const yesterday =
        balances[0].estimated_total_usd * balances[0].estimated_total_btc;
      const previousYesterday =
        balances[1].estimated_total_usd * balances[1].estimated_total_btc;
      const diff = yesterday - previousYesterday;
      revenue = roundDecimals(diff, 4);
      percentage = roundDecimals(diff / previousYesterday, 4) * 100;
    }
    this.setState({ revenue: revenue, percentageRevenue: percentage });
  };

  computeLineChart = (assets) => {
    /**
     * Compute percentage increases benchmark
     * BTC vs Portfolio
     */
    const dates = [];
    const values = [];
    let value = 0;
    for (let i = 0; i < assets.length; i++) {
      if (i === 0) continue;
      const previous =
        assets[i - 1].estimated_total_btc * assets[i - 1].estimated_total_usd;
      const current =
        assets[i].estimated_total_btc * assets[i].estimated_total_usd;
      value += ((previous - current) / previous) * 100;
      const date = assets[i].time;
      dates.push(date);
      values.push(value);
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
    const assetsLegend = {
      name: "Portfolio",
      color: listCssColors[0],
    };

    this.setState({
      lineChartData: [trace],
      lineChartLegend: [assetsLegend],
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

  computeNetWorth = (data) => {
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

  computeDailyPnL = (data) => {
    let dates = [];
    let values = [];
    let colors = [];
    for (let i = 0; i < data.length; i++) {
      if (i === 0) continue;
      const previous =
        data[i - 1].estimated_total_btc * data[i - 1].estimated_total_usd;
      const current = data[i].estimated_total_btc * data[i].estimated_total_usd;
      const value = roundDecimals(previous - current, 4);
      const date = data[i].time;
      dates.push(date);
      values.push(value);
      if (parseFloat(value) > 0) {
        colors.push(listCssColors[0]);
      } else {
        colors.push(listCssColors[7]);
      }
    }
    const trace = {
      x: dates,
      y: values,
      type: "bar",
      marker: {
        color: colors,
        size: 8,
      },
    };

    this.setState({ dailyPnL: [trace] });
  };

  computeUsdBalance = async (balances) => {
    /**
     * As opposed to totalBtcBalance, this balance does not rely on cronjob
     */
    const value = balances.reduce(
      (accumulator, current) =>
        parseFloat(accumulator) + parseFloat(current.btc_value),
      0
    );
    const url = `https://api.alternative.me/v2/ticker/bitcoin/?convert=USD`;
    const response = await request(url);
    const conversionRate = parseFloat(
      response["data"]["1"]["quotes"]["USD"]["price"]
    );
    this.setState({
      usdBalance: roundDecimals(conversionRate * value, 4),
    });
  };

  render() {
    const { balances } = this.props;

    return (
      <>
        <div className="content">
          {!checkValue(balances) ? (
            <>
              <Row>
                <Col lg="4" md="6" sm="6">
                  <Card className="card-stats">
                    <CardBody>
                      <Row>
                        <Col md="12">
                          <div className="stats">
                            <p className="card-category">Balance</p>
                            {balances && (
                              <CardTitle tag="h5" className={`card-title`}>
                                {`${roundDecimals(
                                  balances.reduce(
                                    (accumulator, current) =>
                                      parseFloat(accumulator) +
                                      parseFloat(current.btc_value),
                                    0
                                  ),
                                  6
                                )} BTC`}
                                <br />
                                {`$${this.state.usdBalance}`}
                              </CardTitle>
                            )}
                          </div>
                        </Col>
                      </Row>
                    </CardBody>
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
                            <p className="card-category">Profit &amp; Loss</p>
                            <CardTitle
                              tag="div"
                              className={
                                this.state.revenue > 0
                                  ? "text-success"
                                  : "text-danger"
                              }
                            >
                              <p>
                                {this.state.percentageRevenue &&
                                  `${this.state.percentageRevenue}%`}
                              </p>
                              <p>
                                {this.state.revenue && `$${this.state.revenue}`}
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
                  {this.state.lineChartData && (
                    <PortfolioBenchmarkChart
                      data={this.state.lineChartData}
                      legend={this.state.lineChartLegend}
                    />
                  )}
                </Col>
              </Row>
              <Row>
                <Col md="4">
                  {this.state.netWorth && (
                    <NetWorthChart data={this.state.netWorth} />
                  )}
                  {this.state.dailyPnL && (
                    <ProfitLossBars data={this.state.dailyPnL} />
                  )}
                </Col>
                <Col md="8">
                  <div className="t-jumbotron">
                    <h2>Failed bots</h2>
                  </div>
                </Col>
              </Row>
            </>
          ) : (
            <Row>
              <Col md="12">
                <h1>No balance data available</h1>
              </Col>
            </Row>
          )}
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
