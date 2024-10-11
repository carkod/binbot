import { Badge, Card, Col, Row } from "react-bootstrap"
import { useAppSelector } from "../hooks"
import { selectBot } from "../../features/bots/botSlice"
import { computeSingleBotProfit } from "../../features/bots/profits"
import { roundDecimals } from "../../utils/math"
import { useImmer } from "use-immer"
import { updateOrderLines } from "../../utils/charting/index"
import { type OrderLine } from "../../utils/charting/index.d"
import { updateTimescaleMarks } from "../../utils/charting"
import { TVChartContainer } from "binbot-charts"

// Untyped module
// declare let TVChartContainer: any;

export const ChartContainer = () => {
  const props = useAppSelector(selectBot)
  const botProfit = computeSingleBotProfit(props)
  const [currentChartPrice, setCurrentChartPrice] = useImmer<number>(0)
  const [currentOrderLines, setCurrentOrderLines] = useImmer<OrderLine[]>([])

  const updatedPrice = price => {
    if (currentChartPrice !== parseFloat(price)) {
      const newOrderLines = updateOrderLines(props, price)
      setCurrentOrderLines(newOrderLines)
      setCurrentChartPrice(parseFloat(price))
    }
  }

  const handleInitialPrice = price => {
    if (!props.deal.buy_price && props.status !== "active") {
      setCurrentChartPrice(price)
    }
    const newOrderLines = updateOrderLines(props, price)
    setCurrentOrderLines(newOrderLines)
  }

  return (
    <Card style={{ minHeight: "650px" }}>
      <Card.Header>
        <Row style={{ alignItems: "baseline" }}>
          <Col>
            <Card.Title as="h3">
              {props.pair}{" "}
              <Badge color={botProfit > 0 ? "success" : "danger"}>
                {botProfit ? botProfit + "%" : "0%"}
              </Badge>{" "}
              {props?.status && (
                <Badge
                  color={
                    props.status === "active"
                      ? "success"
                      : props.status === "error"
                        ? "warning"
                        : props.status === "completed"
                          ? "info"
                          : "secondary"
                  }
                >
                  {props.status}
                </Badge>
              )}{" "}
              {props.strategy && <Badge color="info">{props.strategy}</Badge>}
            </Card.Title>
          </Col>
          <Col>
            {botProfit && (
              <h4>
                Earnings after commissions (est.):{" "}
                {roundDecimals(botProfit - 0.3) + "%"}
              </h4>
            )}
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {props?.pair && (
          <TVChartContainer
            symbol={props.pair}
            // Take interval value from autotrade settings
            interval={"1h"}
            timescaleMarks={updateTimescaleMarks(props)}
            orderLines={currentOrderLines}
            onTick={tick => updatedPrice(tick.close)}
            getLatestBar={bar => handleInitialPrice(bar[3])}
          />
        )}
      </Card.Body>
    </Card>
  )
}
