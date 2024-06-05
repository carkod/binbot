import PropTypes from "prop-types";
import { Button } from "react-bootstrap";
import { useHistory } from "react-router-dom";
import {
  Badge,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Col,
  Row
} from "reactstrap";
import { computeSingleBotProfit } from "../state/bots/actions";
import { checkValue, roundDecimals } from "../validations";
import renderTimestamp from "./services/bot-duration";
import { RenderTimestamps } from "./BotCardTs";


const renderSellTimestamp = (bot) => {
  // Long positions
  if (bot.deal) {
    return (
      <>
        {renderTimestamp(bot)}
      </>
    );
  } else {
    return (<></>)
  }
};

const getNetProfit = (bot) => {
  // current price if bot is active
  // sell price if bot is completed
  let netProfit = computeSingleBotProfit(bot);
  if (!netProfit) netProfit = 0;
  return netProfit
};

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
        selectedCards.includes(x.id) ? "is-selected card-stats" : "card-stats"
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
            <CardTitle tag="h5" className="card-title uppercase">
              {!checkValue(x.deal) && (
                <Badge color={getNetProfit(x) > 0 ? "success" : "danger"}>
                  {getNetProfit(x) + "%"}
                </Badge>
              )}
            </CardTitle>
          </Col>
        </Row>
        <Row className="u-align-baseline">
          <Col md="7" xs="12">
            <div className="stats">
              <p className="card-category capitalize">{x.name}</p>
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
                <Col md="7" xs="7">
                  <p className="card-category">Mode</p>
                </Col>
                <Col md="5" xs="5">
                  <p className="card-category capitalize">
                    {!checkValue(x.mode) ? x.mode : "Unknown"}
                  </p>
                </Col>
              </Row>
              <Row>
                <Col md="7" xs="7">
                  <p className="card-category">Strategy</p>
                </Col>
                <Col md="5" xs="5">
                  <p className="card-category capitalize">{x.strategy}</p>
                </Col>
              </Row>
              <Row>
                <Col md="7" xs="7">
                  <p className="card-category">Open @</p>
                </Col>
                <Col md="5" xs="5">
                  <p className="card-category">
                    {(x.deal?.buy_price && roundDecimals(x.deal.buy_price.toFixed(6))) || (x.deal?.buy_total_qty)}
                  </p>
                </Col>
              </Row>
              {x.close_condition && (
                <Row>
                  <Col md="7" xs="7">
                    <p className="card-category">Close condition</p>
                  </Col>
                  <Col md="5" xs="5">
                    <p className="card-category">
                      {x.close_condition}
                    </p>
                  </Col>
                </Row>
              )}
              <Row>
                <Col md="7" xs="7">
                  <p className="card-category">Take profit</p>
                </Col>
                <Col md="5" xs="5">
                  <p className="card-category">{roundDecimals(x.take_profit) + "%"}</p>
                </Col>
              </Row>

              {x.trailling && (
                <Row>
                  <Col md="7" xs="7">
                    <p className="card-category">Trailling loss</p>
                  </Col>
                  <Col md="5" xs="5">
                    <p className="card-category">
                      {roundDecimals(x.trailling_deviation) + "%"}
                    </p>
                  </Col>
                </Row>
              )}

              {parseInt(x.stop_loss) > 0 && (
                <Row>
                  <Col md="7" xs="7">
                    <p className="card-category">Stop loss</p>
                  </Col>
                  <Col md="5" xs="5">
                    <p className="card-category">{roundDecimals(x.stop_loss) + "%"}</p>
                  </Col>
                </Row>
              )}

              {parseFloat(x.commissions) > 0 && (
                <Row>
                  <Col md="7" xs="7">
                    <p className="card-category">Comissions</p>
                  </Col>
                  <Col md="5" xs="5">
                    <p className="card-category">{`${x.commissions} BNB`}</p>
                  </Col>
                </Row>
              )}
            </div>
            <div className="stats">
              {RenderTimestamps(x)}
            </div>
            {!checkValue(x.deal?.buy_timestamp) &&
            !checkValue(x.deal?.sell_timestamp) ? (
              <Row>
                <Col md="7" xs="7">
                  <p className="card-category">Duration</p>
                </Col>
                <Col md="5" xs="5">
                  <p className="card-category">{renderSellTimestamp(x)}</p>
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
            variant="info"
            title="Edit this bot"
            onClick={() =>
              history.push(`${history.location.pathname}/edit/${x.id}`)
            }
          >
            <i className="fa-solid fa-edit u-disable-events" />
          </Button>
          <Button
            variant="success"
            title="Select this bot"
            data-index={tabIndex}
            data-id={x.id}
            onClick={handleSelection}
          >
            <i className="fa-solid fa-check u-disable-events" aria-hidden="true" />
          </Button>
          {x.status !== "active" && (
            <Button
              variant="secondary"
              title="Archive bot"
              onClick={() => {
                archiveBot(x.id);
              }}
            >
              <i className="fas fa-folder u-disable-events" />
            </Button>
          )}
          <Button variant="danger" onClick={() => handleDelete(x.id)}>
            <i className="fas fa-trash u-disable-events" />
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
