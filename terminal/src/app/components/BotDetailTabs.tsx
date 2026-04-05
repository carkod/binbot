import { useEffect, useState, type FC } from "react";
import { Button, Col, Nav, Row, Tab } from "react-bootstrap";
import { useNavigate, useParams } from "react-router";
import {
  botsApiSlice,
  useCreateBotMutation,
  useDeactivateBotMutation,
  useEditBotMutation,
  useLazyActivateBotQuery,
} from "../../features/bots/botsApiSlice";
import { selectBot, setBot } from "../../features/bots/botSlice";
import { BotStatus, MarketType, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import BaseOrderTab from "./BaseOrderTab";
import StopLossTab from "./StopLossTab";
import TakeProfit from "./TakeProfitTab";
import { setSpinner } from "../../features/layoutSlice";

const BotDetailTabs: FC<{
  marketType: MarketType;
  fiatAvailable?: number | null;
}> = ({ marketType, fiatAvailable }) => {
  const { bot } = useAppSelector(selectBot);
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [updateBot] = useEditBotMutation();
  const [createBot] = useCreateBotMutation();
  const [
    trigger,
    { isLoading: isActivating, isError, data: activatedBot, error },
  ] = useLazyActivateBotQuery();
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
    const { data } = await updateBot({ body: bot, id });
    await trigger(id);
    if (id && data) {
      navigate(getEditPath(id));
    }
  };
  const handlePanicSell = async (id: string) => {
    await deactivateBot(id).unwrap();
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
            <BaseOrderTab fiatAvailable={fiatAvailable} />
            <StopLossTab />
            <TakeProfit />
          </Tab.Content>
        </Col>
      </Row>
      <Row>
        <Col lg="3">
          {bot.status !== BotStatus.COMPLETED && (
            <Button
              className="btn-round"
              color="primary"
              onClick={() => {
                handleActivation(bot.id);
              }}
              disabled={!enableActivation}
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
              >
                Panic close
              </Button>
            )}
        </Col>
        <Col lg="3">
          {(bot.status !== BotStatus.ACTIVE ||
            Object.keys(bot.deal).length === 0) && (
            <Button
              className="btn-round"
              color="primary"
              type="submit"
              onClick={onSubmit}
            >
              Save
            </Button>
          )}
        </Col>
      </Row>
    </Tab.Container>
  );
};

export default BotDetailTabs;
