import React from "react";
import { connect } from "react-redux";
import { Button, Card, CardBody, CardFooter, CardHeader, CardTitle, Col, Row } from "reactstrap";
import LineChart from "../../components/LineChart";
import PieChart from "../../components/PieChart";
import { checkValue, listCssColors } from "../../validations";
import { getAssets, getBalance, getBtcChange, updateAssets } from "./actions";

class Dashboard extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      revenue: 0,
      percentageRevenue: "0%",
      lineChartData: null,
      lineChartLegend: null,
      pieChartData: null,
      pieChartLegend: null,
    }
  }

  componentDidMount = () => {
    this.props.getBalance();
    this.props.getAssets();
    this.props.getBtcChange("BTCUSDT", "1d");
  }

  componentDidUpdate = (p, s) => {
    if (!checkValue(this.props.assets) && p.assets !== this.props.assets) {
      this.computePieChart(this.props.assets);
    }
    if (!checkValue(this.props.assets24) && p.assets24 !== this.props.assets24) {
      this.computeDiffAssets(this.props.assets24, this.props.btcChange);
    }

    if (!checkValue(this.props.btcChange) && p.btcChange !== this.props.btcChange) {
      this.computeLineChart(this.props.assets, this.props.btcChange);
    }
  }

  computeDiffAssets = (assets) => {
    const diff = assets[0].total_btc_value - assets[assets.length - 1].total_btc_value;
    const result = Math.floor(diff / assets[assets.length - 1].total_btc_value)
    this.setState({ revenue: diff, percentageRevenue: result })
  }

  computeLineChart = (assets, btcChange) => {
    /**
     * Compute percentage increases benchmark
     * BTC vs Portfolio
     * 
     */
    const dates = []
    const values = []
    assets.forEach((a,i) => {
      const b = assets[i + 1]
      if (b !== undefined) {
        const date = new Date(b.updatedTime * 1000)
        const value = [(a.total_btc_value - b.total_btc_value) / a.total_btc_value] * 100
        dates.push(date)
        values.push(value)
      }
      
    })
    const trace = {
      x: dates,
      y: values,
      type: 'scatter',
      mode: 'lines+markers',
      connectgaps: true,
      line: {
        color: listCssColors[0],
        width: 1
      },
      marker: {
        color: listCssColors[0],
        size: 8
      }
    }
    const assetsLegend = {
      name: "Portfolio",
      color: listCssColors[0]
    }


    // Trace 2
    btcChange.line = {
      color: listCssColors[1],
      width: 1
    };
    btcChange.marker = {
      color: listCssColors[1],
      size: 8
    };
    const btcChangeLegend = {
      name: "BTC on USDT",
      color: listCssColors[1]
    }
    
    this.setState({ lineChartData: [trace, btcChange], lineChartLegend: [assetsLegend, btcChangeLegend] })

  }

  computePieChart = (assets) => {
    let values = [];
    let labels = [];
    let pieChartLegend = [];
    assets[0].balances.forEach((x, i) => {
      values.push(x.free)
      labels.push(x.asset)
      pieChartLegend.push({
        name: x.asset,
        color: listCssColors[i]
      })
    });
    const data = [{
      values: values,
      labels: labels,
      type: 'pie',
      marker: {
        colors: listCssColors
      },
    }];
    this.setState({ pieChartData: data, pieChartLegend: pieChartLegend });
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
            <Col md="4">
              <Card>
                <CardHeader>
                  <CardTitle tag="h5">Portfolio allocation</CardTitle>
                  {/* <p className="card-category">Last Campaign Performance</p> */}
                </CardHeader>
                <CardBody>
                  { this.state.pieChartData && <PieChart data={this.state.pieChartData} /> }
                </CardBody>
                <CardFooter>
                <div className="legend">
                  { this.state.pieChartLegend && this.state.pieChartLegend.map((x, i) => {
                    return (
                      <span key={i} className="u-text-margin-left">
                        <i className="fa fa-circle" style={{"color": x.color}} />
                        {x.name}
                      </span>
                    )
                  })}
                    
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
                  <CardTitle tag="h5">Portfolio benchmarking</CardTitle>
                  <p className="card-category">Compare Portfolio against BTC and USDT</p>
                </CardHeader>
                <CardBody>
                    {this.state.lineChartData && <LineChart data={this.state.lineChartData} /> }
                </CardBody>
                <CardFooter>
                <div className="legend">
                  { this.state.lineChartLegend && this.state.lineChartLegend.map((x, i) => {
                    return (
                      <span key={i} className="u-text-margin-left">
                        <i className="fa fa-circle" style={{"color": x.color}} />
                        {x.name}
                      </span>
                    )
                  })}
                    
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

const twenty4assets = (assets) => {
  let filterAssets = assets.filter((x) => {
    const date = new Date();
    const yesterday = date.setDate(date.getDate() - 1)
    const updatedTime = x.updatedTime * 1000
    if ((updatedTime < new Date().getTime()) && (updatedTime > yesterday)) {
      return true
    }
    return false;
  })
  let sortAsset = filterAssets.sort((a,b) => b.updatedTime - a.updatedTime);
  return sortAsset;
}
    

const mapStateToProps = (s) => {
  const { data: balances } = s.balanceReducer;
  const { data: assets } = s.assetsReducer;
  const { data: btcChange } = s.btcChangeReducer;
  let props = {
    balances: balances,
    assets: assets,
    assets24: null,
    btcChange: btcChange,
  }
  if (!checkValue(assets)) {
    const assets24 = twenty4assets(assets);
    props.assets24 = assets24;
  }
  return props;

}

export default connect(mapStateToProps, { getBalance, getAssets, updateAssets, getBtcChange })(Dashboard);
