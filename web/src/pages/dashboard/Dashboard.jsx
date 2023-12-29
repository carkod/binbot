import produce from "immer";
import moment from "moment";
import React from "react";
import { Col, Row } from "react-bootstrap";
import { connect } from "react-redux";
import { Card, CardBody, CardFooter, CardTitle } from "reactstrap";
import GainersLosers from "../../components/GainersLosers";
import GainersLosersGraph from "../../components/GainersLosersGraph";
import { loading } from "../../containers/spinner/actions";
import { getBalanceRaw, getEstimate } from "../../state/balances/actions";
import { checkValue, listCssColors, roundDecimals } from "../../validations";
import { NetWorthChart } from "./NetWorthChart";
import { PortfolioBenchmarkChart } from "./PortfolioBenchmarkChart";
import { ProfitLossBars } from "./ProfitLossBars";
import {
  getBenchmarkData,
  getBenchmarkUsdt,
  getGainersLosers,
  getGainersLosersSeries,
} from "./saga";
import VolumesRankingCard from "../../components/VolumesRanking";

class Dashboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      revenue: 0,
      percentageRevenue: 0,
      lineChartData: null,
      lineChartLegend: null,
      pieChartData: null,
      pieChartLegend: null,
      netWorth: null,
      netWorthLegend: null,
      networthLayout: null,
      dailyPnL: null,
      usdBalance: 0, // Does not rely on cronjob totalBtcBalance
      btcPrices: [],
    };
  }

  getBtcprices = async (periods = 86400) => {
    const startDate = moment().subtract(1, "months").valueOf();
    const options = {
      contentType: "application/json",
      mode: "cors",
      cache: "no-cache",
    };
    const response = await fetch(
      `https://api.cryptowat.ch/markets/binance/BTCUSDT/ohlc?periods=${periods}&value=${startDate}`,
      options
    );
    const data = response.json();
    const btcPrices = produce(this.state, (draft) => {
      draft.selectedCards.push(data);
    });
    this.setState({ btcPrices: btcPrices });
  };

  componentDidMount = () => {
    this.props.getBalanceRaw();
    this.props.getEstimate();
    this.props.getGainersLosers();
    this.props.getGainersLosersSeries();
    this.props.getBenchmarkData();
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

  render() {
    const { balanceEstimate, load, gainersLosersSeries } = this.props;
    return (
      <>
        <div className="content">
          {!load ? (
            <>
              <Row>
                <Col lg="3" md="12" sm="12" xs="12">
                  <div id="dashboard-grid">
                    <Card className="card-stats">
                      <CardBody>
                        <Row>
                          <Col md="12">
                            {balanceEstimate && (
                              <div className="stats">
                                <Row>
                                  <Col md="4" xs="5">
                                    <div className="icon-big text-center icon-warning">
                                      <i className="nc-icon nc-money-coins text-success" />
                                    </div>
                                  </Col>
                                  <Col md="8" xs="7">
                                    <p className="card-category u-text-right">
                                      Total Balance
                                    </p>
                                    <CardTitle
                                      tag="h3"
                                      className="card-title numbers"
                                    >
                                      {roundDecimals(
                                        balanceEstimate.total_fiat,
                                        2
                                      )}{" "}
                                      {balanceEstimate.asset}
                                      <br />
                                    </CardTitle>
                                  </Col>
                                </Row>
                              </div>
                            )}
                          </Col>
                        </Row>
                      </CardBody>
                      {balanceEstimate && (
                        <CardFooter>
                          <hr />
                          <Row>
                            <Col>
                              <p className="card-category">Left to allocate:</p>
                            </Col>
                            <Col>
                              <p className="card-category u-text-right">
                                {balanceEstimate.fiat_left}{" "}
                                {balanceEstimate.asset}
                              </p>
                            </Col>
                          </Row>
                        </CardFooter>
                      )}
                    </Card>
                    <Card className="card-stats">
                      <CardBody>
                        <Row>
                          <Col md="4" xs="5">
                            <div className="icon-big text-center icon-warning">
                              <i className="nc-icon nc-bank text-success" />
                            </div>
                          </Col>
                          <Col md="8" xs="7">
                            <div className="stats">
                              <p className="card-category u-text-right">
                                Profit &amp; Loss
                              </p>
                              <CardTitle
                                tag="h3"
                                className={
                                  this.props.percentageRevenue > 0
                                    ? "text-success card-title numbers"
                                    : "text-danger card-title numbers"
                                }
                              >
                                <p>
                                  {typeof this.props.percentageRevenue ===
                                    "number" &&
                                    `${this.props.percentageRevenue.toFixed(
                                      2
                                    )}% `}
                                </p>
                              </CardTitle>
                              <p />
                            </div>
                          </Col>
                        </Row>
                      </CardBody>
                      <CardFooter>
                        <hr />
                        <Row>
                          <Col>
                            <p className="card-category">
                              (Current - Last balance)
                            </p>
                          </Col>
                          <Col>
                            <p className="card-category u-text-right">
                              {typeof this.props.revenue === "number" &&
                                this.props.revenue.toFixed(4)}{" "}
                              USDT
                            </p>
                          </Col>
                        </Row>
                      </CardFooter>
                    </Card>
                  </div>
                </Col>
                <Col lg="9">
                  {this.props.benchmarkData.dates?.btc && (
                    <PortfolioBenchmarkChart
                      data={this.props.benchmarkData}
                      legend={this.state.lineChartLegend}
                    />
                  )}
                </Col>
              </Row>
              <Row>
                <Col lg="6" md="12">
                  {this.props.gainersLosersData?.length > 0 && (
                    <GainersLosers data={this.props.gainersLosersData} />
                  )}
                </Col>
                <Col lg="6" md="12">
                  {gainersLosersSeries && (
                    <GainersLosersGraph
                      data={gainersLosersSeries}
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
              <Row>
                <Col lg="6" md="12">
                  {this.props.gainersLosersData && this.props.gainersLosersData.length > 0 && (
                    <VolumesRankingCard data={this.props.gainersLosersData} title="Today's highest volumes in USDT market"/>
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
  const { data: balanceEstimate } = s.estimateReducer;
  const { data: balance_raw } = s.balanceRawReducer;
  const { data: gainersLosersData } = s.gainersLosersReducer;
  const { data: gainersLosersSeries } = s.gainersLosersSeriesReducer;

  const {
    data: benchmarkData,
    btcPrices,
    usdtBalanceSeries,
    dates,
  } = s.btcBenchmarkReducer;
  let percentageRevenue = 0;
  let revenue = 0;

  if (benchmarkData && balanceEstimate) {
    revenue = balanceEstimate.total_fiat - benchmarkData.usdt[0];
    percentageRevenue = (revenue / balanceEstimate.total_fiat) * 100;
  }

  return {
    loading: loading,
    assetList: balance_raw,
    balanceEstimate: balanceEstimate,
    gainersLosersData: gainersLosersData,
    gainersLosersSeries: gainersLosersSeries,
    benchmarkData: {
      usdt: usdtBalanceSeries,
      btc: btcPrices,
      dates: dates,
    },
    percentageRevenue: percentageRevenue,
    revenue: revenue,
  };
};

export default connect(mapStateToProps, {
  loading,
  getEstimate,
  getBalanceRaw,
  getGainersLosers,
  getGainersLosersSeries,
  getBenchmarkData,
  getBenchmarkUsdt,
})(Dashboard);
