import type { FC } from "react"
import { useEffect } from "react"
import { Card, Col, Container, Row } from "react-bootstrap"
import { useMatch, useParams } from "react-router"
import { useGetSingleBotQuery } from "../../features/bots/botsApiSlice"
import { selectBot, setBot } from "../../features/bots/botSlice"
import BotDetailTabs from "../components/BotDetailTabs"
import BotInfo from "../components/BotInfo"
import ChartContainer from "../components/ChartContainer"
import { useAppDispatch, useAppSelector } from "../hooks"
import LogsInfo from "../components/LogsInfo"
import BalanceAnalysis from "../components/BalanceAnalysis"
import { useGetEstimateQuery } from "../../features/balanceApiSlice"
import { singleBot } from "../../features/bots/botInitialState"

export const BotDetail: FC<{}> = () => {
  const { id } = useParams()
  const matchNewRoute = useMatch("/bots/new")
  const dispatch = useAppDispatch()
  const { bot } = useAppSelector(selectBot)
  const { data } = useGetSingleBotQuery(id, { skip: Boolean(!id) })
  const { data: accountData } = useGetEstimateQuery()

  useEffect(() => {
    if (data && !matchNewRoute) {
      dispatch(setBot(data))
    } else {
      dispatch(setBot({
        bot: singleBot
      }))
    }
  }, [data, matchNewRoute, dispatch])

  return (
    <div className="content">
      <Container fluid>
        <Row>
          <Col md="12" sm="12">
            <ChartContainer />
          </Col>
        </Row>
        {bot && id && (
          <Row>
            <Col md="7" sm="12">
              <BotInfo bot={bot} />
            </Col>
            <Col md="5" sm="12">
              {bot.errors?.length > 0 && <LogsInfo events={bot.errors} />}
            </Col>
          </Row>
        )}

        <Row>
          <Col md="7" sm="12">
            <Card>
              <Card.Body>
                <BotDetailTabs  />
              </Card.Body>
            </Card>
          </Col>
          <Col md="5" sm="12">
              {accountData && (
                <BalanceAnalysis accountData={accountData} />
              )}
            </Col>
        </Row>
      </Container>
    </div>
  )
}

export default BotDetail
