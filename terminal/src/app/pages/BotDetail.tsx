import type { FC } from "react"
import { useEffect } from "react"
import { Card, Col, Container, Nav, Row, Tab } from "react-bootstrap"
import { set, useForm } from "react-hook-form"
import { type LoginFormState } from "../components/LoginForm"
import { useLocation, useMatch, useParams } from "react-router"
import {
  useGetBotsQuery,
  useGetSingleBotQuery,
} from "../../features/bots/botsApiSlice"
import BotDetailTabs from "../components/BotDetailTabs"
import { singleBot } from "../../features/bots/botInitialState"
import { selectBot, setBot } from "../../features/bots/botSlice"
import { useAppSelector } from "../hooks"
import { ChartContainer } from "../components/ChartContainer"

export enum TabsKeys {
  MAIN = "main",
  STOPLOSS = "stop-loss",
  TAKEPROFIT = "take-profit",
}

export const BotDetail: FC<{}> = () => {
  const { id } = useParams()
  const props = useAppSelector(selectBot)
  const { data } = useGetSingleBotQuery(id, {skip: !id})

  useEffect(() => {
    if (data) {
      setBot(data)
    }
  }, [data])

  return (
    <div className="content">
      <Container fluid>
        <Row>
          <Col md="12" sm="12">
            <ChartContainer />
          </Col>
        </Row>
        <Row>
          {/* 
          {!checkValue(this.props.bot) &&
          !checkValue(this.props.match.params.id) ? (
            <>
              <Col md="7" sm="12">
                <BotInfo bot={this.props.bot} />
              </Col>
              <Col md="5" sm="12">
                {this.props.bot.errors?.length > 0 && (
                  <LogsInfo events={this.props.bot.errors} />
                )}
              </Col>
            </>
          ) : (
            ""
          )} */}
        </Row>
        <Row>
          <Col md="7" sm="12">
            <Card>
              <Card.Body>
                <BotDetailTabs bot={props} />
              </Card.Body>
            </Card>
          </Col>
          <Col md="5" sm="12"></Col>
        </Row>
      </Container>
    </div>
  )
}

export default BotDetail