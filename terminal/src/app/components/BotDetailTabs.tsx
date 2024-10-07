import { type FC } from "react"
import { Col, Nav, Row, Tab } from "react-bootstrap"
import { type Bot } from "../../features/bots/botInitialState"
import { TabsKeys } from "../pages/BotDetail"
import BaseOrderTab from "./BaseOrderTab"

const BotDetailTabs: FC<{
  bot: Bot
}> = ({ bot }) => {

  return (
    <Tab.Container defaultActiveKey={TabsKeys.MAIN}>
      <Row>
        <Col sm={12}>
          <Nav variant="tabs">
            <Nav.Item>
              <Nav.Link eventKey={TabsKeys.MAIN}>Base order</Nav.Link>
            </Nav.Item>
            <Nav.Item>
              {/* <Nav.Link eventKey="second">Tab 2</Nav.Link> */}
            </Nav.Item>
          </Nav>
        </Col>
        <Col sm={12}>
          <Tab.Content>
            <BaseOrderTab bot={bot} />
            {/* <Tab.Pane eventKey="second">Second tab content</Tab.Pane> */}
          </Tab.Content>
        </Col>
      </Row>
    </Tab.Container>
  )
}

export default BotDetailTabs
