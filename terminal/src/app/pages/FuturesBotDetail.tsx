import { Box, Card, Grid } from "@mantine/core";
import { useContext, useEffect, type FC } from "react";
import { useParams } from "react-router";
import { useGetBalanceQuery } from "../../features/balanceApiSlice";
import { useGetSingleBotQuery } from "../../features/bots/botsApiSlice";
import {
  resetBot,
  selectBot,
  setBot,
  setCurrentPrice,
} from "../../features/bots/botSlice";
import { MarketType } from "../../utils/enums";
import BalanceAnalysis from "../components/BalanceAnalysis";
import BotChartTabs from "../components/BotChartTabs";
import BotDetailTabs from "../components/BotDetailTabs";
import BotInfo from "../components/BotInfo";
import LogsInfo from "../components/LogsInfo";
import { useAppDispatch, useAppSelector } from "../hooks";
import { SymbolProvider } from "../providers/SymbolProvider";
import { SpinnerContext } from "../spinner-context";
export const FuturesBotDetail: FC<{}> = () => {
  const { id, symbol } = useParams();
  const isNewBot = !id;
  const dispatch = useAppDispatch();
  const { bot } = useAppSelector(selectBot);
  const { data, isLoading: loadingBot } = useGetSingleBotQuery(id as string, {
    skip: Boolean(!id),
  });
  const { data: accountData, isLoading: loadingEstimates } =
    useGetBalanceQuery();
  const { setSpinner } = useContext(SpinnerContext);
  const currentMarketType = MarketType.FUTURES;
  useEffect(() => {
    if (isNewBot) {
      dispatch(
        resetBot({
          market_type: MarketType.FUTURES,
          pair: symbol ?? "",
        }),
      );
    } else if (data?.bot) {
      dispatch(
        setBot({
          bot: { ...data.bot, market_type: MarketType.FUTURES },
        }),
      );
    } else {
      dispatch(
        resetBot({
          market_type: MarketType.FUTURES,
          pair: symbol ?? "",
        }),
      );
    }
    if (!loadingBot && !loadingEstimates) {
      setSpinner(false);
    } else {
      setSpinner(true);
    }
  }, [
    data,
    isNewBot,
    dispatch,
    loadingBot,
    loadingEstimates,
    setSpinner,
    symbol,
  ]);
  return (
    <SymbolProvider marketType={currentMarketType}>
      <div className="content">
        <Box w="100%">
          <BotChartTabs
            bot={bot}
            setCurrentPrice={setCurrentPrice}
            marketType={currentMarketType}
          />
          {bot && id && (
            <Grid>
              <Grid.Col span={{ base: 12, md: 7 }}>
                <BotInfo bot={bot} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 5 }}>
                {bot.logs?.length > 0 && <LogsInfo events={bot.logs} />}
              </Grid.Col>
            </Grid>
          )}

          <Grid>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Card mb="md">
                <Box>
                  <BotDetailTabs
                    marketType={currentMarketType}
                    fiatAvailable={accountData?.fiat_available}
                  />
                </Box>
              </Card>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 5 }}>
              {accountData && (
                <BalanceAnalysis
                  accountData={accountData}
                  marketType={currentMarketType}
                />
              )}
            </Grid.Col>
          </Grid>
        </Box>
      </div>
    </SymbolProvider>
  );
};
export default FuturesBotDetail;
