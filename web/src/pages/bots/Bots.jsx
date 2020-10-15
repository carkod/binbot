import React from "react";
import { connect } from "react-redux";
import { Button, Card, CardBody, CardFooter, CardHeader, CardTitle, Col, Jumbotron, Row, ButtonToggle } from "reactstrap";
import { getBots } from "./actions";
class Bots extends React.Component {

  constructor(props) {
    super(props);
    this.state = {}
  }

  componentDidMount = () => {
    this.props.getBots();
  }

  convertPercent = (stringNum) => {
    return `${parseFloat(stringNum) * 100}%`
  }

  render() {
    const { bots } = this.props;
    console.log(bots)
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              <Card>
                <CardHeader>
                  <CardTitle tag="h5">Users Behavior</CardTitle>
                  <p className="card-category">24 Hours performance</p>
                </CardHeader>
                <CardBody>
                  GRAPH GOES HERE
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
            <Col md="12">
              <Jumbotron>
                <h2 className="display-5">All bots</h2>
                <p className="lead">Ordered by active and creation date</p>
              </Jumbotron>
            </Col>
          </Row>
          <Row>
            {bots && bots.map((x, i) =>
              <Col key={x._id.$oid} lg='4'>
                <Card className="card-stats">
                  <CardBody>
                  <Row>
                    <Col md="7" xs="12">
                      <div className="stats">
                        <CardTitle tag='h5' className="card-title">
                          {x.pair}
                          </CardTitle>
                      </div>
                    </Col>
                    <Col md="5" xs="12">
                      <CardTitle tag='h5' className="card-title u-uppercase">
                        { x.strategy === "short" ? <i className="fas fa-chart-line" /> : <i className="fa fa-angle-double-up" /> }
                        {` ${x.strategy}`}
                      </CardTitle>
                    </Col>
                  </Row>
                  <Row className="u-align-baseline">
                    <Col md="7" xs="12">
                      <div className="stats">
                        <p className="card-category">{x.name}</p>
                      </div>
                    </Col>
                    <Col md="4" xs="12">
                        {x.active === "true" ? <ButtonToggle color="success">On</ButtonToggle> : <ButtonToggle color="secondary">Off</ButtonToggle>}
                    </Col>
                  </Row>
                  <hr />
                  <Row>
                    <Col md="7" xs="12">
                      <div className="stats">
                        <p className="card-category">Balance Use</p>
                        <p className="card-category">SO size</p>
                        <p className="card-category">SO deviation</p>
                        <p className="card-category">Take Profit</p>
                        { x.trailling === "true" && <p className="card-category">Trailling TP</p> }
                      </div>
                    </Col>
                    <Col md="4" xs="12">
                      <div className="stats">
                        <p className="card-category">{this.convertPercent(x.balance_usage)}</p>
                        <p className="card-category">{x.so_size}</p>
                        <p className="card-category">{this.convertPercent(x.price_deviation_so)}</p>
                        <p className="card-category">{this.convertPercent(x.take_profit)}</p>
                        { x.trailling === "true" && <p className="card-category">{x.trailling_deviation}</p> }
                      </div>
                    </Col>
                  </Row>
                  </CardBody>
                  <CardFooter>
                    <hr />
                    <div className="stats">
                      <Button color="link"><i className="fas fa-sync-alt" /> Update Now</Button>
                    </div>
                  </CardFooter>
                </Card>
              </Col>
            )}
            
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  if (state.botReducer.data) {
    // Sort active status first
    const bots = state.botReducer.data.sort((a,b) => {
      if (a.active === "true") {
        return -1
      } else {
        return 1
      }
    });
    return {
      ...state.botReducer,
      bots: bots,
    }
  }
  return state;
  
}

export default connect(mapStateToProps, { getBots })(Bots);