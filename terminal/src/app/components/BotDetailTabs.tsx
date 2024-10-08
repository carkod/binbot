import { useState, type FC } from "react"
import { Button, Col, Nav, Row, Tab } from "react-bootstrap"
import { type Bot } from "../../features/bots/botInitialState"
import { TabsKeys } from "../pages/BotDetail"
import BaseOrderTab from "./BaseOrderTab"
import { BotStatus } from "../../utils/enums"
import StopLossTab from "./StopLossTab"
import TakeProfit from "./TakeProfitTab"

const BotDetailTabs: FC<{
  bot: Bot
}> = ({ bot }) => {
  const [activeTab, setActiveTab] = useState<TabsKeys>(TabsKeys.MAIN)

  const handleTabClick = (tab: TabsKeys) => {
    setActiveTab(tab)
  }

  const handleActivation = (id: string) => {
    console.log("Activate bot", id)
  }
  const handlePanicSell = (id: string) => {
    console.log("Panic sell", id)
  }

  return (
    <Tab.Container defaultActiveKey={TabsKeys.MAIN}>
      <Row>
        <Col sm={12}>
          <Nav variant="tabs">
            <Nav.Item>
              <Nav.Link eventKey={TabsKeys.MAIN}>Base order</Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link eventKey={TabsKeys.STOPLOSS}>Stop Loss</Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link eventKey={TabsKeys.TAKEPROFIT}>Take Profit</Nav.Link>
            </Nav.Item>
          </Nav>
        </Col>
        <Col sm={12}>
          <Tab.Content>
            <BaseOrderTab bot={bot} />
            <StopLossTab bot={bot} />
            <TakeProfit bot={bot} />
          </Tab.Content>
        </Col>
      </Row>
      <Row>
        <Col lg="3">
          {bot.status !== BotStatus.COMPLETED && (
            <Button
              className="btn-round"
              color="primary"
              onClick={() => handleActivation(bot.id)}
              disabled
            >
              {bot.status === BotStatus.ACTIVE &&
              Object.keys(bot.deal).length > 0
                ? "Update deal"
                : "Deal"}
            </Button>
          )}
        </Col>
        <Col lg="3">
          {bot.status === BotStatus.ACTIVE &&
            Object.keys(bot.deal).length > 0 && (
              <Button
                className="btn-round"
                color="primary"
                onClick={() => handlePanicSell(bot.id)}
                disabled
              >
                Panic close
              </Button>
            )}
        </Col>
        <Col lg="3">
          {(bot.status !== BotStatus.ACTIVE ||
            Object.keys(bot.deal).length === 0) && (
            <Button className="btn-round" color="primary" type="submit">
              Save
            </Button>
          )}
        </Col>
      </Row>
    </Tab.Container>
  )
}

export default BotDetailTabs
