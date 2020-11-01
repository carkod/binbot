import React from "react";
import { Line, Pie } from "react-chartjs-2";
import { Card, CardHeader, CardBody, CardFooter, CardTitle, Row, Col, Button } from "reactstrap";
import { dashboard24HoursPerformanceChart, dashboardEmailStatisticsChart, dashboardNASDAQChart } from "variables/charts.jsx";
import { getBalance, getAssets, updateAssets } from "./actions";
import { connect } from "react-redux";
import { checkValue } from "validations";

class Dashboard extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      revenue: 0
    }
  }

  componentDidMount = () => {
    this.props.getBalance();
    this.props.getAssets();
  }

  componentDidUpdate = (p, s) => {
    if (!checkValue(this.props.assets) && p.assets !== this.props.assets) {
      this.computeDiffAssets(this.props.assets)
    }
  }

  computeDiffAssets = (assets) => {
    const diff = assets[0].total_btc_value - assets[assets.length - 1].total_btc_value;
    const result = Math.floor(diff / assets[assets.length - 1].total_btc_value)
    this.setState({ revenue: diff, percentageRevenue: result })
  }

  updateAssets = () => {
    this.props.updateAssets();
  }

  render() {
    const { balances, assets } = this.props
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
                        {balances && balances.map((x, i) =>
                          <CardTitle key={i} tag="h5" className={`card-title`} >
                            <span className={Math.max.apply(Math, balances.map((o) => o.free)) === x.free ? "u-green-badge" : ""} >
                              {x.free}
                            </span>
                          </CardTitle>
                        )}

                      </div>
                    </Col>
                    <Col md="4" xs="12">
                      <div className="stats">
                        <p className="card-category">Asset</p>
                        {balances && balances.map((x, i) =>
                          <CardTitle key={i} tag="h5" className="card-title">{x.asset}</CardTitle>
                        )}
                      </div>
                    </Col>
                  </Row>
                </CardBody>
                <CardFooter>
                  <hr />
                  <div className="stats">
                    { assets && `Total ${ parseFloat(assets[0].total_btc_value).toFixed(6)} BTC` }
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
                        <p className="card-category">Revenue</p>
                        <CardTitle tag="p" className={this.state.revenue > 0 ? "text-success" : "text-danger"}>{this.state.percentageRevenue && this.state.percentageRevenue + " %"}</CardTitle>
                        <p />
                      </div>
                    </Col>
                  </Row>
                </CardBody>
                <CardFooter>
                  <hr />
                  <div className="stats">
                    <Button color="link" title="Click to store balance" onClick={this.updateAssets}><i className="fas fa-sync" /> Last 24 hours</Button>
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
            <Col md="12">
              <Card>
                <CardHeader>
                  <CardTitle tag="h5">Users Behavior</CardTitle>
                  <p className="card-category">24 Hours performance</p>
                </CardHeader>
                <CardBody>
                  <Line
                    data={dashboard24HoursPerformanceChart.data}
                    options={dashboard24HoursPerformanceChart.options}
                    width={400}
                    height={100}
                  />
                </CardBody>
                <CardFooter>
                  <hr />
                  <div className="stats">
                    <i className="fa fa-history" /> Updated 3 minutes ago
                  </div>
                </CardFooter>
              </Card>
            </Col>
          </Row>
          <Row>
            <Col md="4">
              <Card>
                <CardHeader>
                  <CardTitle tag="h5">Email Statistics</CardTitle>
                  <p className="card-category">Last Campaign Performance</p>
                </CardHeader>
                <CardBody>
                  <Pie
                    data={dashboardEmailStatisticsChart.data}
                    options={dashboardEmailStatisticsChart.options}
                  />
                </CardBody>
                <CardFooter>
                  <div className="legend">
                    <i className="fa fa-circle text-primary" /> Opened{" "}
                    <i className="fa fa-circle text-warning" /> Read{" "}
                    <i className="fa fa-circle text-danger" /> Deleted{" "}
                    <i className="fa fa-circle text-gray" /> Unopened
                  </div>
                  <hr />
                  <div className="stats">
                    <i className="fa fa-calendar" /> Number of emails sent
                  </div>
                </CardFooter>
              </Card>
            </Col>
            <Col md="8">
              <Card className="card-chart">
                <CardHeader>
                  <CardTitle tag="h5">NASDAQ: AAPL</CardTitle>
                  <p className="card-category">Line Chart with Points</p>
                </CardHeader>
                <CardBody>
                  <Line
                    data={dashboardNASDAQChart.data}
                    options={dashboardNASDAQChart.options}
                    width={400}
                    height={100}
                  />
                </CardBody>
                <CardFooter>
                  <div className="chart-legend">
                    <i className="fa fa-circle text-info" /> Tesla Model S{" "}
                    <i className="fa fa-circle text-warning" /> BMW 5 Series
                  </div>
                  <hr />
                  <div className="card-stats">
                    <i className="fa fa-check" /> Data information certified
                  </div>
                </CardFooter>
              </Card>
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { data: balances } = state.balanceReducer;
  const { data: assets } = state.assetsReducer;
  return {
    balances: balances,
    assets: assets
  }

}

export default connect(mapStateToProps, { getBalance, getAssets, updateAssets })(Dashboard);
