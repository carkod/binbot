import React, { useContext, type FC, useEffect } from "react";
import { Card, Col, Container, Row } from "react-bootstrap";
import { useMatch, useParams } from "react-router";
import { useGetSingleBotQuery } from "../../features/bots/botsApiSlice";
import {
  resetBot,
  selectBot,
  setBot,
  setCurrentPrice,
} from "../../features/bots/botSlice";
import BotDetailTabs from "../components/BotDetailTabs";
import BotInfo from "../components/BotInfo";
import ChartContainer from "../components/ChartContainer";
import { useAppDispatch, useAppSelector } from "../hooks";
import LogsInfo from "../components/LogsInfo";
import { singleBot } from "../../features/bots/botInitialState";
import { SpinnerContext } from "../Layout";
import { useGetBalanceQuery } from "../../features/balanceApiSlice";
import BalanceAnalysis from "../components/BalanceAnalysis";
import { SymbolProvider } from "../providers/SymbolProvider";
import { MarketType } from "../../utils/enums";

export const FuturesBotDetail: FC<{}> = () => {
  const { id } = useParams();
  const matchNewRoute = useMatch("/bots/futures/new");
  const dispatch = useAppDispatch();
  const { bot } = useAppSelector(selectBot);
  const { data, isLoading: loadingBot } = useGetSingleBotQuery(id as string, {
    skip: Boolean(!id),
  });
  const { data: accountData, isLoading: loadingEstimates } =
    useGetBalanceQuery();
  const { spinner, setSpinner } = useContext(SpinnerContext);
  const currentMarketType = bot?.market_type ?? MarketType.FUTURES;

  useEffect(() => {
    if (matchNewRoute) {
      dispatch(resetBot());
      return;
    }
    if (data?.bot) {
      dispatch(
        setBot({
          bot: { ...data.bot },
        }),
      );
    } else {
      dispatch(
        setBot({
          bot: { ...singleBot, market_type: MarketType.FUTURES },
        }),
      );
    }

    if (!loadingBot && !loadingEstimates) {
      setSpinner(false);
    } else {
      setSpinner(true);
    }
  }, [data, matchNewRoute, dispatch, loadingBot, loadingEstimates, setSpinner]);

  return (
    <SymbolProvider marketType={currentMarketType}>
      <div className="content">
        <Container fluid>
          <Row>
            <Col md="12" sm="12">
              <ChartContainer
                bot={bot}
                setCurrentPrice={setCurrentPrice}
                marketType={currentMarketType}
              />
            </Col>
          </Row>
          {bot && id && (
            <Row>
              <Col md="7" sm="12">
                <BotInfo bot={bot} />
              </Col>
              <Col md="5" sm="12">
                {bot.logs?.length > 0 && <LogsInfo events={bot.logs} />}
              </Col>
            </Row>
          )}

          <Row>
            <Col md="7" sm="12">
              <Card>
                <Card.Body>
                  <BotDetailTabs marketType={currentMarketType} />
                </Card.Body>
              </Card>
            </Col>
            <Col md="5" sm="12">
              {accountData && (
                <BalanceAnalysis
                  accountData={accountData}
                  marketType={currentMarketType}
                />
              )}
            </Col>
          </Row>
        </Container>
      </div>
    </SymbolProvider>
  );
};

export default FuturesBotDetail;
