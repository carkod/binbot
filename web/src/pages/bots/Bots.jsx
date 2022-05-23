import { produce } from "immer";
import moment from "moment";
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
  FormGroup,
  Input,
  Row,
} from "reactstrap";
import ConfirmModal from "../../components/ConfirmModal";
import {
  getProfit,
  setFilterByMonthState,
  setFilterByWeek,
  weekAgo,
} from "../../state/bots/actions";
import { checkValue } from "../../validations";
import { archiveBot, closeBot, deleteBot, getBots } from "./actions";
import { Form } from "react-bootstrap";

class Bots extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      confirmModal: null,
      selectedCards: [],
      totalProfit: 0,
      dateFilterError: ""
    };

    this.startDate = React.createRef();
    this.endDate = React.createRef();
  }

  componentDidMount = () => {
    // Default values for date filtering
    let startDate = new Date(weekAgo());
    
    // Temporary fix - get tomorrow's endDate to include today's bot
    const today = new Date()
    let endDate = new Date(today);
    endDate.setDate(endDate.getDate() + 1)
    this.startDate.valueAsDate = startDate;
    this.endDate.valueAsDate = endDate;

    // Convert to millseconds for endpoint
    startDate = this.startDate.valueAsNumber;
    endDate = this.endDate.valueAsNumber;
    this.props.getBots({ startDate, endDate });
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
      this.props.deleteBot([this.state.confirmModal]);
    } else {
      this.props.closeBot(this.state.confirmModal);
    }
    this.setState({ confirmModal: null });
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
            this.props.deleteBot(this.state.selectedCards);
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

  handleDateFilters = (e) => {
    const startDate = this.startDate.valueAsNumber;
    const endDate = this.endDate.valueAsNumber;
    if (startDate >= endDate) {
      this.setState({
        dateFilterError: "Start date must be earlier than end date"
      });
      return
    }
    if (checkValue(startDate) || checkValue(endDate)) {
      this.props.getBots();
    } else {
      this.props.getBots({ startDate, endDate });
    }
    this.setState({
      dateFilterError: ""
    });
  };

  render() {
    const { bots } = this.props;
    return (
      <>
        <div className="content">
          <Form>
            <FormGroup row>
              <Col sm={2}>
                <h3>
                  <Badge
                    color={this.props.totalProfit > 0 ? "success" : "danger"}
                  >
                    <i className="nc-icon nc-bank" />{" "}
                    {this.props.totalProfit + "%"}
                  </Badge>
                </h3>
              </Col>
              <Col sm={2}>
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
              <Col sm={2}>
                <Button onClick={this.onSubmitBulkAction}>
                  Apply action
                </Button>
              </Col>
              <Col sm={2}>
                <label htmlFor="startDate">Filter by start date</label>
                <Form.Control
                  type="date"
                  name="startDate"
                  ref={(element) => (this.startDate = element)}
                  onBlur={this.handleDateFilters}
                  isInvalid={!checkValue(this.state.dateFilterError)}
                />
              </Col>
              <Col sm={2}>
                <label htmlFor="endDate">Filter by end date</label>
                <Form.Control
                  type="date"
                  name="endDate"
                  onBlur={this.handleDateFilters}
                  ref={(element) => (this.endDate = element)}
                  isInvalid={!checkValue(this.state.dateFilterError)}
                />
                {!checkValue(this.state.dateFilterError) &&
                  <Form.Control.Feedback type="invalid">{this.state.dateFilterError}</Form.Control.Feedback>
                }
              </Col>
            </FormGroup>
          </Form>

          <Row>
            {!checkValue(bots)
              ? bots.map((x, i) => (
                  <Col key={x._id.$oid} sm="6" md="4" lg="3">
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
                                    getProfit(
                                      x.deal.buy_price,
                                      x.deal.current_price
                                    ) > 0
                                      ? "success"
                                      : "danger"
                                  }
                                >
                                  {getProfit(
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
                              {parseInt(x.deal?.buy_timestamp) > 0 && (
                                <Row>
                                  <Col md="7">
                                    <p className="card-category">Buy time</p>
                                  </Col>
                                  <Col md="5">
                                    <p className="card-category">
                                      {moment(x.deal?.buy_timestamp).format(
                                        "D, MMM, hh:mm"
                                      )}
                                    </p>
                                  </Col>
                                </Row>
                              )}

                              {parseInt(x.deal?.sell_timestamp) > 0 && (
                                <Row>
                                  <Col md="7">
                                    <p className="card-category">Sell time</p>
                                  </Col>
                                  <Col md="5">
                                    <p className="card-category">
                                      {moment(x.deal?.sell_timestamp).format(
                                        "D MMM, hh:mm"
                                      )}
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
                                `/admin/bots/edit/${x._id.$oid}`
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
          acceptText={"Close"}
          cancelText={"Delete"}
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
  const { message, bots, totalProfit } = state.botReducer;
  return {
    bots: bots,
    message: message,
    totalProfit: totalProfit,
  };
};

export default connect(mapStateToProps, {
  getBots,
  deleteBot,
  closeBot,
  archiveBot,
  setFilterByWeek,
  setFilterByMonthState,
})(Bots);
