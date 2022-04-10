import { produce } from "immer";
import React from "react";
import { connect } from "react-redux";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Col,
  Container,
  Form,
  FormGroup,
  Input,
  Row,
} from "reactstrap";
import ConfirmModal from "../../components/ConfirmModal";
import { checkValue } from "../../validations";
import { closeTestBot, deleteTestBot, getTestBots } from "./actions";

class TestBots extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      confirmModal: null,
      selectedCards: [],
    };
  }

  componentDidMount = () => {
    this.props.getTestBots();
  };

  componentDidUpdate = (p, s) => {
    if (this.props.bots !== p.bots) {
      this.computeTotalProfit(this.props.bots);
    }
  };

  handleChange = (e) => {
    this.setState({
      [e.target.name]: e.target.value,
    });
  };

  convertPercent = (stringNum) => {
    return `${parseFloat(stringNum) * 100}%`;
  };

  handleDelete = (id) => {
    this.setState({ confirmModal: id });
  };

  confirmDelete = (option) => {
    if (parseInt(option) === 1) {
      this.props.deleteTestBot([this.state.confirmModal]);
      this.props.getTestBots();
    }
    this.setState({ confirmModal: null });
  };

  getProfit = (base_price, current_price) => {
    if (!checkValue(base_price) && !checkValue(current_price)) {
      const percent =
        ((parseFloat(current_price) - parseFloat(base_price)) /
          parseFloat(base_price)) *
        100;
      return percent.toFixed(2);
    }
    return 0;
  };

  handleSelection = (e) => {
    if (!checkValue(e.target.dataset.id)) {
      if (!this.state.selectedCards.includes(e.target.dataset.id)) {
        const addCard = produce(this.state, (draft) => {
          draft.selectedCards.push(e.target.dataset.id);
        });
        this.setState(addCard);
      } else {
        const unselectedCard = produce(this.state, (draft) => {
          const index = draft.selectedCards.findIndex(
            (x) => x === e.target.dataset.id
          );
          draft.selectedCards.splice(index, 1);
        });
        this.setState(unselectedCard);
      }
    }
  };

  onSubmitBulkAction = () => {
    if (!checkValue(this.state.bulkActions)) {
      const value = this.state.bulkActions;
      switch (value) {
        case "delete-selected":
          if (this.state.selectedCards.length > 0) {
            this.props.deleteTestBot(this.state.selectedCards);
            this.props.getTestBots();
            this.setState({
              selectedCards: [],
            });
          }
          break;
        case "unselect-all":
          const unselectAll = produce(this.state, (draft) => {
            draft.selectedCards = [];
          });
          this.setState(unselectAll);
          break;
        case "select-all":
          const selectAll = produce(this.state, (draft) => {
            let selectedCards = [];
            this.props.bots.forEach((element) => {
              selectedCards.push(element._id.$oid);
            });
            draft.selectedCards = selectedCards;
            return draft;
          });
          this.setState(selectAll);
          break;
        default:
          break;
      }
    }
  };

  computeTotalProfit = (bots) => {
    if (bots) {
      const totalProfit = bots
        .map((bot) => bot.deal)
        .reduce((accumulator, currBot) => {
          let currTotalProfit = this.getProfit(
            currBot.buy_price,
            currBot.current_price
          );
          return parseFloat(accumulator) + parseFloat(currTotalProfit);
        }, 0);
      this.setState({
        totalProfit: totalProfit.toFixed(2),
      });
    }
  };

  render() {
    const { bots } = this.props;
    return (
      <>
        <Container>
          <Form>
            <FormGroup row>
              <Col sm={3}>
                <h3>
                  <Badge
                    color={this.state.totalProfit > 0 ? "success" : "danger"}
                  >
                    <i className="nc-icon nc-bank" />{" "}
                    {this.state.totalProfit + "%"}
                  </Badge>
                </h3>
              </Col>
              <Col sm={4}>
                <Input
                  bsSize="sm"
                  type="select"
                  name="bulkActions"
                  id="bulk-actions"
                  onChange={this.handleChange}
                >
                  <option value="">Select bulk action</option>
                  <option value="delete-selected">Delete selected</option>
                  <option value="unselect-all">Unselect all</option>
                  <option value="select-all">Select all</option>
                </Input>
              </Col>
              <Col sm={3}>
                <Button onClick={this.onSubmitBulkAction}>
                  Apply bulk action
                </Button>
              </Col>
            </FormGroup>
          </Form>
        </Container>
        <div className="content">
          <Row>
            {!checkValue(bots)
              ? bots.map((x, i) => (
                  <Col key={i} sm="6" md="4" lg="3">
                    <Card
                      tabIndex={i}
                      className={
                        this.state.selectedCards.includes(x._id.$oid)
                          ? "is-selected card-stats"
                          : "card-stats"
                      }
                    >
                      <CardBody>
                        <Row>
                          <Col md="7" xs="12">
                            <div className="stats">
                              <CardTitle tag="h5" className="card-title">
                                {x.pair}
                              </CardTitle>
                            </div>
                          </Col>
                          <Col md="5" xs="12">
                            <CardTitle
                              tag="h5"
                              className="card-title u-uppercase"
                            >
                              {!checkValue(x.deal) && (
                                <Badge
                                  color={
                                    this.getProfit(
                                      x.deal.buy_price,
                                      x.deal.current_price
                                    ) > 0
                                      ? "success"
                                      : "danger"
                                  }
                                >
                                  {this.getProfit(
                                    x.deal.buy_price,
                                    x.deal.current_price
                                  ) + "%"}
                                </Badge>
                              )}
                            </CardTitle>
                          </Col>
                        </Row>
                        <Row className="u-align-baseline">
                          <Col md="7" xs="12">
                            <div className="stats">
                              <p className="card-category">{x.name}</p>
                            </div>
                          </Col>
                          <Col md="5" xs="12">
                            <div className="stats">
                              <Badge
                                color={
                                  x.status === "active"
                                    ? "success"
                                    : x.status === "error"
                                    ? "warning"
                                    : x.status === "completed"
                                    ? "info"
                                    : "secondary"
                                }
                              >
                                {!checkValue(x.status) &&
                                  x.status.toUpperCase()}
                              </Badge>
                            </div>
                          </Col>
                        </Row>
                        <hr />
                        <Row>
                          <Col md="12" xs="12">
                            <div className="stats">
                              <Row>
                                <Col md="7">
                                  <p className="card-category">Mode</p>
                                </Col>
                                <Col md="5">
                                  <p className="card-category">
                                    {!checkValue(x.mode) ? x.mode : "Unknown"}
                                  </p>
                                </Col>
                              </Row>
                              <Row>
                                <Col md="7">
                                  <p className="card-category">
                                    # Safety Orders
                                  </p>
                                </Col>
                                <Col md="5">
                                  <p className="card-category">
                                    {x.max_so_count}
                                  </p>
                                </Col>
                              </Row>

                              <Row>
                                <Col md="7">
                                  <p className="card-category">Bought @</p>
                                </Col>
                                <Col md="5">
                                  <p className="card-category">
                                    {!checkValue(x.deal) && x.deal.buy_price}
                                  </p>
                                </Col>
                              </Row>

                              <Row>
                                <Col md="7">
                                  <p className="card-category">Take profit</p>
                                </Col>
                                <Col md="5">
                                  <p className="card-category">
                                    {x.take_profit + "%"}
                                  </p>
                                </Col>
                              </Row>

                              {x.trailling === "true" && (
                                <Row>
                                  <Col md="7">
                                    <p className="card-category">
                                      Trailling loss
                                    </p>
                                  </Col>
                                  <Col md="5">
                                    <p className="card-category">
                                      {x.trailling_deviation + "%"}
                                    </p>
                                  </Col>
                                </Row>
                              )}

                              {parseInt(x.stop_loss) > 0 && (
                                <Row>
                                  <Col md="7">
                                    <p className="card-category">Stop loss</p>
                                  </Col>
                                  <Col md="5">
                                    <p className="card-category">
                                      {x.stop_loss + "%"}
                                    </p>
                                  </Col>
                                </Row>
                              )}

                              {parseFloat(x.commissions) > 0 && (
                                <Row>
                                  <Col md="7">
                                    <p className="card-category">Comissions</p>
                                  </Col>
                                  <Col md="5">
                                    <p className="card-category">
                                      {`${x.commissions} BNB`}
                                    </p>
                                  </Col>
                                </Row>
                              )}
                            </div>
                          </Col>
                        </Row>
                      </CardBody>
                      <CardFooter>
                        <hr />
                        <div className="u-space-between">
                          <Button
                            color="info"
                            title="Edit this bot"
                            onClick={() =>
                              this.props.history.push(
                                `/admin/paper-trading/edit/${x._id.$oid}`
                              )
                            }
                          >
                            <i className="fas fa-edit" />
                          </Button>
                          <Button
                            color="success"
                            title="Select this bot"
                            data-index={i}
                            data-id={x._id.$oid}
                            onClick={this.handleSelection}
                          >
                            <i className="fas fa-check" />
                          </Button>
                          {x.status !== "active" && (
                            <Button
                              color="secondary"
                              title="Archive bot"
                              onClick={() => {
                                this.props.archiveBot(x._id.$oid);
                              }}
                            >
                              <i className="fas fa-folder" />
                            </Button>
                          )}
                          <Button
                            color="danger"
                            onClick={() => this.handleDelete(x._id.$oid)}
                          >
                            <i className="fas fa-trash" />
                          </Button>
                        </div>
                      </CardFooter>
                    </Card>
                  </Col>
                ))
              : "No data available"}
          </Row>
        </div>
        <ConfirmModal
          close={() => this.setState({ confirmModal: null })}
          modal={this.state.confirmModal}
          handleActions={this.confirmDelete}
          acceptText={"Close orders, sell coins and delete bot"}
          cancelText={"Just delete bot"}
        >
          Closing deals will close outstanding orders, sell coins and delete bot
        </ConfirmModal>
        {this.state.selectedCards.length > 0 && (
          <ConfirmModal>
            You did not select the items for bulk action
          </ConfirmModal>
        )}
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { message, bots } = state.testBotsReducer;
  if (bots && bots.length > 0) {
    return {
      bots: bots,
      message: message,
    };
  }

  return {};
};

export default connect(mapStateToProps, {
  getTestBots,
  deleteTestBot,
  closeTestBot,
})(TestBots);
