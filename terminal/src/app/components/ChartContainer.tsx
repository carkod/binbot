import { Badge, Card, Col, Row } from "react-bootstrap"
import { useAppSelector } from "../hooks"
import { selectBot } from "../../features/bots/botSlice"
import { computeSingleBotProfit } from "../../features/bots/profits"
import { roundDecimals } from "../../utils/math"
import { useImmer } from "use-immer"
import { updateOrderLines } from "../../utils/charting/index"
import { type OrderLine } from "../../utils/charting/index.d"
import { updateTimescaleMarks } from "../../utils/charting"
import TVChartContainer from "binbot-charts"
import { type ResolutionString } from "../../../charting_library/charting_library"

const ChartContainer = () => {
  const { bot } = useAppSelector(selectBot)
  const botProfit = computeSingleBotProfit(bot)
  const [currentChartPrice, setCurrentChartPrice] = useImmer<number>(0)
  const [currentOrderLines, setCurrentOrderLines] = useImmer<OrderLine[]>([])

  const updatedPrice = price => {
    price = roundDecimals(price, 4)
    if (currentChartPrice !== parseFloat(price)) {
      const newOrderLines = updateOrderLines(bot, price)
      setCurrentOrderLines(newOrderLines)
      setCurrentChartPrice(parseFloat(price))
    }
  }

  const handleInitialPrice = price => {
    if (!bot.deal.buy_price && bot.status !== "active") {
      setCurrentChartPrice(price)
    }
    const newOrderLines = updateOrderLines(bot, price)
    setCurrentOrderLines(newOrderLines)
  }

  return (
    <Card style={{ minHeight: "650px" }}>
      <Card.Header>
        <Row style={{ alignItems: "baseline" }}>
          <Col md="8">
            <Card.Title as="h3">
              {bot.pair}{" "}
              <Badge bg={botProfit > 0 ? "success" : botProfit < 0 ? "danger" : "secondary"}>
                {botProfit ? botProfit + "%" : "0%"}
              </Badge>{" "}
              <Badge
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
                {bot.status}
              </Badge>{" "}
            <Badge color="info">{bot.strategy}</Badge>
            </Card.Title>
          </Col>
          <Col md="12" lg="4">
            {botProfit && botProfit > 0 && (
              <small className="fs-6 fw-light">
                Earnings after commissions (est.):{" "}
                {roundDecimals(botProfit - bot.commissions) + "%"}
              </small>
            )}
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {bot?.pair && (
          <TVChartContainer
            symbol={bot.pair}
            // Take interval value from autotrade settings
            interval={"1h" as ResolutionString}
            timescaleMarks={updateTimescaleMarks(bot)}
            orderLines={currentOrderLines}
            onTick={tick => updatedPrice(parseFloat(tick.close))}
            getLatestBar={bar => handleInitialPrice(parseFloat(bar[3]))}
          />
        )}
      </Card.Body>
    </Card>
  )
}

export default ChartContainer
