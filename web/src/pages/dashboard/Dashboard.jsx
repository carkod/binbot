import React from "react";
import { connect } from "react-redux";
import { Card, CardBody, CardFooter, CardTitle, Col, Row } from "reactstrap";
import { checkValue, listCssColors, roundDecimals } from "../../validations";
import { AssetsTable } from "../../components/AssetsTable";
import { NetWorthChart } from "./NetWorthChart";
import { PortfolioBenchmarkChart } from "./PortfolioBenchmarkChart";
import { ProfitLossBars } from "./ProfitLossBars";
import request from "../../request";
import { loading } from "../../containers/spinner/actions";
import { getBalance } from "../../state/balances/actions";
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
    this.props.getBalance();
  };

  componentDidUpdate = (p, s) => {
    if (
      !checkValue(this.props.balances) &&
      p.balances !== this.props.balances
    ) {
      this.computeLineChart(this.props.balances);
    }
    if (
      !checkValue(this.props.balanceDiff) &&
      p.balanceDiff !== this.props.balanceDiff
    ) {
      this.computeDiffAssets(this.props.balanceDiff);
      this.computeNetWorth(this.props.balanceDiff);
      this.computeDailyPnL(this.props.balanceDiff);
    }
  };

  computeDiffAssets = (assets) => {
    const balances = assets.reverse();
    let revenue,
      percentage = "N/A";
    if (balances.length > 1) {
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
    assets.forEach((x, i) => {
      dates.push(x.time);
      values.push(x.estimated_total_btc);
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

    this.setState({
      lineChartData: [trace],
      lineChartLegend: [assetsLegend]
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
    const { balances, load } = this.props;

    return (
      <>
        <div className="content">
          {!load ? (
              <>
                <Row>
                  <Col lg="4" md="6" sm="6">
                    <Card className="card-stats">
                      <CardBody>
                        <Row>
                          <Col md="12">
                            <div className="stats">
                              <p className="card-category">Total Balance</p>
                              {!checkValue(balances) && balances.length > 0 ? (
                                <CardTitle tag="h3" className={`card-title`}>
                                  {`${roundDecimals(
                                    balances[0].estimated_total_gbp,
                                    2
                                  )} £`}
                                  <hr />
                                  {`${roundDecimals(
                                    balances[0].estimated_total_btc,
                                    8
                                  )} BTC`}
                                </CardTitle>
                              ) : ""}
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
                                  {this.state.percentageRevenue > 0 &&
                                    `${this.state.percentageRevenue.toFixed(
                                      2
                                    )}%`}
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
                </Row>
                <Row>
                  <Col md="4">
                  {!checkValue(balances) && balances.length > 0 ? (
                    <AssetsTable
                      data={this.props.balances[0]["balances"]}
                      headers={["Symbol", "Free", "Locked"]}
                    />
                  ) : ""}
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
                  <Col md="12">
                    {this.state.netWorth && (
                      <NetWorthChart data={this.state.netWorth} />
                    )}
                    {this.state.dailyPnL && (
                      <ProfitLossBars data={this.state.dailyPnL} />
                    )}
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
  const { loading } = s.loadingReducer;
  const { data: balances } = s.balanceReducer;
  return {
    balances: balances,
    loading: loading
  };
};

export default connect(mapStateToProps, {
  getBalance,
  loading
})(Dashboard);
