import React, { type FC } from "react";
import { Badge, Button, Card, Col, Container, Row } from "react-bootstrap";
import { useNavigate } from "react-router";
import { type Bot } from "../../features/bots/botInitialState";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { roundDecimals } from "../../utils/math";
import { BotStatus } from "../../utils/enums";
import { formatTimestamp, renderDuration } from "../../utils/time";
import { getQuoteAsset } from "../../utils/api";

type handleCallback = (id: string) => void;

interface BotCardProps {
  bot: Bot;
  botIndex?: number; // Selected bot index, this can be one of the selectedCards array
  selectedCards?: string[]; // Collection of selected cards
  handleSelection?: handleCallback;
  handleDelete?: handleCallback;
}

/**
 * Dump component that displays bots
 * in a card format
 * All logic should be handled in the parent component
 * @param BotCardProps
 * @returns React.Component
 */
const BotCard: FC<BotCardProps> = ({
  bot,
  botIndex,
  selectedCards,
  handleSelection,
  handleDelete,
}) => {
  const botProfit = computeSingleBotProfit(bot);
  const navigate = useNavigate();
  return (
    <Card
      tabIndex={botIndex}
      className={selectedCards.includes(bot.id) ? "border border-success" : ""}
    >
      <Card.Body>
        <Container fluid>
          <Row>
            <Col md="7" xs="12">
              <Card.Title as="h5">{bot.pair}</Card.Title>
              <small className="text-muted fw-lighter">{bot.name}</small>
            </Col>
            <Col md="5" xs="12">
              <Badge bg={botProfit > 0 ? "success" : "danger"}>
                {roundDecimals(botProfit)}%
              </Badge>
              <br />
              <Badge
                className="small"
                bg={
                  bot.status === "active"
                    ? "success"
                    : bot.status === "error"
                      ? "warning"
                      : bot.status === "completed"
                        ? "info"
                        : "secondary"
                }
              >
                <small>{bot.status && bot.status.toUpperCase()}</small>
              </Badge>
            </Col>
          </Row>
          <hr />
          <Row>
            <Col md="6" xs="7">
              <p className="small">Mode</p>
            </Col>
            <Col md="6" xs="5">
              <p className="small capitalize">
                {bot.mode ? bot.mode : "Unknown"}
              </p>
            </Col>
          </Row>
          <Row>
            <Col md="6" xs="7">
              <p className="small">Strategy</p>
            </Col>
            <Col md="6" xs="5">
              <p className="small capitalize">{bot.strategy}</p>
            </Col>
          </Row>
          <Row>
            <Col md="6" xs="7">
              <p className="small">Open @</p>
            </Col>
            <Col md="6" xs="5">
              <p className="small">
                {(bot.deal?.opening_price &&
                  roundDecimals(bot.deal.opening_price, 6)) ||
                  bot.deal?.opening_qty}
              </p>
            </Col>
          </Row>
          {bot.deal?.opening_timestamp > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Open time</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">
                  {formatTimestamp(bot.deal.opening_timestamp)}
                </p>
              </Col>
            </Row>
          )}
          {bot.trailling ? (
            <>
              <Row>
                <Col md="6" xs="7">
                  <p className="small">Trailling profit</p>
                </Col>
                <Col md="6" xs="5">
                  <p className="small">
                    {roundDecimals(bot.trailling_profit) + "%"}
                  </p>
                </Col>
              </Row>
              <Row>
                <Col md="6" xs="7">
                  <p className="small">Trailling deviation</p>
                </Col>
                <Col md="6" xs="5">
                  <p className="small">
                    {roundDecimals(bot.trailling_deviation) + "%"}
                  </p>
                </Col>
              </Row>
            </>
          ) : (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Take profit</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">{roundDecimals(bot.take_profit) + "%"}</p>
              </Col>
            </Row>
          )}

          {bot.stop_loss > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small small">Stop loss</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">{roundDecimals(bot.stop_loss) + "%"}</p>
              </Col>
            </Row>
          )}

          {bot.deal?.total_commissions > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Comissions</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">{`${bot.deal.total_commissions} BNB`}</p>
              </Col>
            </Row>
          )}
          {bot.deal?.total_interests > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Interests</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">{`${bot.deal.total_interests} ${getQuoteAsset(bot)}`}</p>
              </Col>
            </Row>
          )}

          {bot.deal?.closing_timestamp > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Close time</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">
                  {formatTimestamp(bot.deal.closing_timestamp)}
                </p>
              </Col>
            </Row>
          )}
          {bot.deal?.closing_timestamp > 0 && (
            <Row>
              <Col md="6" xs="7">
                <p className="small">Duration</p>
              </Col>
              <Col md="6" xs="5">
                <p className="small">{renderDuration(bot)}</p>
              </Col>
            </Row>
          )}
        </Container>
      </Card.Body>
      <hr className="hr-compact" />
      <Card.Footer className="d-flex flex-row justify-content-between">
        <Button
          variant="info"
          title="Edit this bot"
          onClick={() =>
            navigate(`/bots/edit/${bot.id}`, {
              state: { bot: bot },
            })
          }
        >
          <i className="fa-solid fa-edit u-disable-events" />
        </Button>
        <Button variant="success" onClick={() => handleSelection(bot.id)}>
          <i className="fa-solid fa-check" />
          <span className="visually-hidden">
            {selectedCards.includes(bot.id) ? "Deselect" : "Select"}
          </span>
        </Button>
        <Button variant="danger" onClick={() => handleDelete(bot.id)}>
          <i className="fa-solid fa-trash" />
          <span className="visually-hidden">Delete</span>
        </Button>
      </Card.Footer>
    </Card>
  );
};

export default BotCard;
