import { useState, type FC } from "react"
import { Button } from "react-bootstrap"
import {
  Badge,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Col,
  Row,
} from "reactstrap"
import { RenderTimestamp } from "./RenderTs"
import { roundDecimals } from "../../utils/math"
import { computeSingleBotProfit } from "../../features/bots/profits"
import { type Bot } from "../../features/bots/botInitialState"

interface BotCardProps {
  bot: Bot
  botIndex?: number  // Selected bot index, this can be one of the selectedCards array
  selectedCards?: number[] // Collection of selected cards
  handleSelection?: (id: number) => void
  handleDelete?: (id: number) => void
}

const renderSellTimestamp = (bot: Bot) => {
  // Long positions
  if (bot.deal) {
    return <>{RenderTimestamp(bot)}</>
  } else {
    return <></>
  }
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
  return (
    <Card>
      <CardBody>
        <CardTitle tag="h5">{bot.name}</CardTitle>
        <Row>
          <Col>
            <Badge color="primary">
              {roundDecimals(computeSingleBotProfit(bot))}%
            </Badge>
          </Col>
          <Col>{renderSellTimestamp(bot)}</Col>
        </Row>
      </CardBody>
      <CardFooter>
        <Button variant="primary" onClick={() => handleSelection(bot.id)}>
          {selectedCards.includes(bot.id) ? "Deselect" : "Select"}
        </Button>
        <Button variant="danger" onClick={() => handleDelete(bot.id)}>
          Delete
        </Button>
      </CardFooter>
    </Card>
  )
}

export default BotCard
