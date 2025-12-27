import React, { type FC } from "react";
import { useEffect } from "react";
import { Card, Col, Container, Row } from "react-bootstrap";
import { useMatch, useParams } from "react-router";
import {
  selectTestBot,
  setTestBot,
  setTestBotCurrentPrice,
} from "../../features/bots/paperTradingSlice";
import BotInfo from "../components/BotInfo";
import ChartContainer from "../components/ChartContainer";
import { useAppDispatch, useAppSelector } from "../hooks";
import LogsInfo from "../components/LogsInfo";
import BalanceAnalysis from "../components/BalanceAnalysis";
import { singleBot } from "../../features/bots/botInitialState";
import PaperTradingDetailTabs from "../components/PaperTradingDetailTabs";
import { useGetSingleTestBotQuery } from "../../features/bots/paperTradingApiSlice";
import { useGetBalanceQuery } from "../../features/balanceApiSlice";

export const PaperTradingDetail: FC = () => {
  const { id } = useParams();
  const matchNewRoute = useMatch("/paper-trading/new");
  const dispatch = useAppDispatch();
  const { paperTrading } = useAppSelector(selectTestBot);
  const { data } = useGetSingleTestBotQuery(id, { skip: Boolean(!id) });
  const { data: accountData } = useGetBalanceQuery();

  useEffect(() => {
    if (data && !matchNewRoute) {
      dispatch(setTestBot(data));
    } else {
      dispatch(
        setTestBot({
          bot: singleBot,
        }),
      );
    }
  }, [data, matchNewRoute, dispatch]);

  return (
    <div className="content">
      <Container fluid>
        <Row>
          <Col md="12" sm="12">
            <ChartContainer
              bot={paperTrading}
              setCurrentPrice={setTestBotCurrentPrice}
            />
          </Col>
        </Row>
        {paperTrading && id && (
          <Row>
            <Col md="7" sm="12">
              <BotInfo bot={paperTrading} />
            </Col>
            <Col md="5" sm="12">
              {paperTrading.logs?.length > 0 && (
                <LogsInfo events={paperTrading.logs} />
              )}
            </Col>
          </Row>
        )}

        <Row>
          <Col md="7" sm="12">
            <Card>
              <Card.Body>
                <PaperTradingDetailTabs />
              </Card.Body>
            </Card>
          </Col>
          <Col md="5" sm="12">
            {accountData && <BalanceAnalysis accountData={accountData} />}
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default PaperTradingDetail;
