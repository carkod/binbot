import Candlestick from "components/Candlestick";
import React from "react";
import { connect } from "react-redux";
import { Button, ButtonToggle, Card, CardBody, CardFooter, CardTitle, Col, Jumbotron, Row } from "reactstrap";
import { deleteBot, getBots } from "./actions";
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

  handleNew = () => {
    this.props.history.replace("/admin/bots-create");
  }

  handleDelete = (id) => {
    this.props.deleteBot(id);
  }

  render() {
    const { bots } = this.props;
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              {"Candlestick goes here"}
              {/* <Candlestick title={"BNBBTC"} /> */}
            </Col>
          </Row>
          <Row>
            <Col md="12">
              <Jumbotron>
                <div className="u-space-between">
                  <h2 className="display-5">All bots</h2>
                  <Button color="link" onClick={this.handleNew}>New bot</Button>
                </div>
                
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
                    <div className="u-space-between">
                      <Button color="info" onClick={() => this.props.history.push(`/admin/bots-edit/${x._id.$oid}`)}><i className="fas fa-edit" /></Button>
                      <Button color="danger" onClick={() => this.handleDelete(x._id.$oid)}><i className="fas fa-trash" /></Button>
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

export default connect(mapStateToProps, { getBots, deleteBot })(Bots);
