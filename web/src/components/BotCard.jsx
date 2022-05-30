import moment from "moment";
import PropTypes from "prop-types";
import { useHistory } from "react-router-dom";
import {
	Badge,
	Button,
	Card,
	CardBody,
	CardFooter,
	CardTitle,
	Col,
	Row
} from "reactstrap";
import { botDuration, getProfit } from "../state/bots/actions";
import { checkValue, roundDecimals } from "../validations";

export default function BotCard({
  tabIndex,
  x,
  selectedCards,
  archiveBot,
  handleDelete,
  handleSelection,
}) {
  const history = useHistory();
  return (
    <Card
      tabIndex={tabIndex}
      className={
        selectedCards.includes(x._id.$oid)
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
            <CardTitle tag="h5" className="card-title u-uppercase">
              {!checkValue(x.deal) && (
                <Badge
                  color={
                    getProfit(x.deal.buy_price, x.deal.current_price) > 0
                      ? "success"
                      : "danger"
                  }
                >
                  {getProfit(x.deal.buy_price, x.deal.current_price) + "%"}
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
                {!checkValue(x.status) && x.status.toUpperCase()}
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
                  <p className="card-category"># Safety Orders</p>
                </Col>
                <Col md="5">
                  <p className="card-category">{x.max_so_count}</p>
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
                  <p className="card-category">{x.take_profit + "%"}</p>
                </Col>
              </Row>

              {x.trailling === "true" && (
                <Row>
                  <Col md="7">
                    <p className="card-category">Trailling loss</p>
                  </Col>
                  <Col md="5">
                    <p className="card-category">
                      {roundDecimals(x.trailling_deviation) + "%"}
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
                    <p className="card-category">{x.stop_loss + "%"}</p>
                  </Col>
                </Row>
              )}

              {parseFloat(x.commissions) > 0 && (
                <Row>
                  <Col md="7">
                    <p className="card-category">Comissions</p>
                  </Col>
                  <Col md="5">
                    <p className="card-category">{`${x.commissions} BNB`}</p>
                  </Col>
                </Row>
              )}
            </div>
            {parseInt(x.deal?.buy_timestamp) > 0 && (
              <Row>
                <Col md="7">
                  <p className="card-category">Buy time</p>
                </Col>
                <Col md="5">
                  <p className="card-category">
                    {moment(x.deal?.buy_timestamp).format("D, MMM, hh:mm")}
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
                    {moment(x.deal?.sell_timestamp).format("D MMM, hh:mm")}
                  </p>
                </Col>
              </Row>
            )}
            {!checkValue(x.deal?.buy_timestamp) &&
            !checkValue(x.deal?.sell_timestamp) ? (
              <Row>
                <Col md="7">
                  <p className="card-category">Duration</p>
                </Col>
                <Col md="5">
                  <p className="card-category">
                    {botDuration(x.deal.buy_timestamp, x.deal.sell_timestamp)}
                  </p>
                </Col>
              </Row>
            ) : (
              ""
            )}
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
              history.push(`${history.location.pathname}/edit/${x._id.$oid}`)
            }
          >
            <i className="fas fa-edit" />
          </Button>
          <Button
            color="success"
            title="Select this bot"
            data-index={tabIndex}
            data-id={x._id.$oid}
            onClick={handleSelection}
          >
            <i className="fas fa-check" />
          </Button>
          {x.status !== "active" && (
            <Button
              color="secondary"
              title="Archive bot"
              onClick={() => {
                archiveBot(x._id.$oid);
              }}
            >
              <i className="fas fa-folder" />
            </Button>
          )}
          <Button color="danger" onClick={() => handleDelete(x._id.$oid)}>
            <i className="fas fa-trash" />
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

BotCard.propTypes = {
  tabIndex: PropTypes.number.isRequired,
  x: PropTypes.shape({
    pair: PropTypes.string.isRequired,
  }),
  selectedCards: PropTypes.arrayOf(PropTypes.string),
  history: PropTypes.func.isRequired,
  archiveBot: PropTypes.func.isRequired,
  handleDelete: PropTypes.func.isRequired,
  handleSelection: PropTypes.func.isRequired,
};
