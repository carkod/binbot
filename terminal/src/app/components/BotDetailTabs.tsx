import { Box, Button, SimpleGrid, Tabs } from "@mantine/core";
import { useEffect, useState, type FC } from "react";
import { useNavigate, useParams } from "react-router";
import {
  useActivateBotMutation,
  useCreateBotMutation,
  useDeactivateBotMutation,
  useEditBotMutation,
} from "../../features/bots/botsApiSlice";
import { selectBot, setBot } from "../../features/bots/botSlice";
import { setSpinner } from "../../features/layoutSlice";
import { BotStatus, MarketType, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import BaseOrderTab from "./BaseOrderTab";
import StopLossTab from "./StopLossTab";
import TakeProfit from "./TakeProfitTab";
const BotDetailTabs: FC<{
  marketType: MarketType;
  fiatAvailable?: number | null;
  activeTab?: TabsKeys;
  onTabChange?: (tab: string | null) => void;
}> = ({ marketType, fiatAvailable, activeTab, onTabChange }) => {
  const { bot } = useAppSelector(selectBot);
  const { id } = useParams<{
    id: string;
  }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [updateBot] = useEditBotMutation();
  const [createBot] = useCreateBotMutation();
  const [trigger, { isLoading: isActivating, data: activatedBot }] =
    useActivateBotMutation();
  const [deactivateBot, { isLoading: isDeactivating, data: deactivatedBot }] =
    useDeactivateBotMutation();
  const [enableActivation, setEnableActivation] = useState(id ? true : false);
  const getEditPath = (botId: string) =>
    marketType === MarketType.FUTURES
      ? `/bots/futures/edit/${botId}`
      : `/bots/edit/${botId}`;
  // Activate and get bot again
  // Deals and orders information need to come from the server
  const handleActivation = async (id: string) => {
    try {
      const data = await updateBot({ body: bot, id }).unwrap();
      if (data?.bot) {
        await trigger(id).unwrap();
        navigate(getEditPath(id));
      }
    } catch {
      // The mutation displays the server error; keep the bot page open.
    }
  };
  const handlePanicSell = async (id: string) => {
    try {
      await deactivateBot(id).unwrap();
    } catch {
      // The mutation displays the server error; keep the bot page open.
    }
  };
  const onSubmit = async () => {
    if (id && bot.status !== BotStatus.COMPLETED) {
      await updateBot({ body: bot, id });
      navigate(getEditPath(id));
    } else {
      const submitData = { ...bot, id: undefined };
      const { data } = await createBot(submitData);
      setEnableActivation(true);
      navigate(getEditPath(data.bot.id));
    }
  };
  useEffect(() => {
    if (isActivating || isDeactivating) {
      dispatch(setSpinner(true));
    } else {
      if (activatedBot) {
        dispatch(setBot({ bot: activatedBot.bot }));
      }
      if (deactivatedBot) {
        dispatch(setBot({ bot: deactivatedBot.bot }));
      }
      dispatch(setSpinner(false));
    }
  }, [isActivating, isDeactivating, dispatch, activatedBot, deactivatedBot]);
  return (
    <Tabs
      key={`${marketType}-${id ?? "new"}-${bot.id}`}
      defaultValue={TabsKeys.MAIN}
      value={activeTab}
      onChange={onTabChange}
      keepMounted={true}
      keepMountedMode="display-none"
    >
      <SimpleGrid cols={1}>
        <Tabs.List>
          <>
            <Tabs.Tab value={TabsKeys.MAIN}>Base order</Tabs.Tab>
          </>
          <>
            <Tabs.Tab value={TabsKeys.STOPLOSS}>Stop Loss</Tabs.Tab>
          </>
          <>
            <Tabs.Tab value={TabsKeys.TAKEPROFIT}>Take Profit</Tabs.Tab>
          </>
        </Tabs.List>
        <Box>
          <BaseOrderTab fiatAvailable={fiatAvailable} />
          <StopLossTab />
          <TakeProfit />
        </Box>
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, lg: 4 }}>
        <Box>
          {bot.status !== BotStatus.COMPLETED && (
            <Button
              color="primary"
              onClick={() => {
                handleActivation(bot.id);
              }}
              disabled={!enableActivation}
              type="button"
              radius="xl"
            >
              {bot.status === BotStatus.ACTIVE &&
              Object.keys(bot.deal).length > 0
                ? "Update deal"
                : "Deal"}
            </Button>
          )}
        </Box>
        <Box>
          {bot.status === BotStatus.ACTIVE &&
            Object.keys(bot.deal).length > 0 && (
              <Button
                color="primary"
                onClick={() => handlePanicSell(bot.id)}
                type="button"
                radius="xl"
              >
                Panic close
              </Button>
            )}
        </Box>
        <Box>
          {(bot.status !== BotStatus.ACTIVE ||
            Object.keys(bot.deal).length === 0) && (
            <Button
              color="primary"
              type="submit"
              onClick={onSubmit}
              radius="xl"
            >
              Save
            </Button>
          )}
        </Box>
      </SimpleGrid>
    </Tabs>
  );
};
export default BotDetailTabs;
