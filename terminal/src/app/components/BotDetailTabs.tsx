import React, { useEffect, useState, type FC } from "react";
import { Button, Col, Nav, Row, Tab } from "react-bootstrap";
import { useNavigate, useParams } from "react-router";
import {
  botsApiSlice,
  useCreateBotMutation,
  useEditBotMutation,
  useLazyActivateBotQuery,
} from "../../features/bots/botsApiSlice";
import { selectBot, setBot } from "../../features/bots/botSlice";
import { BotStatus, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import BaseOrderTab from "./BaseOrderTab";
import StopLossTab from "./StopLossTab";
import TakeProfit from "./TakeProfitTab";
import { setSpinner } from "../../features/layoutSlice";

const BotDetailTabs: FC = () => {
  const { bot } = useAppSelector(selectBot);
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [updateBot] = useEditBotMutation();
  const [createBot] = useCreateBotMutation();
  const [trigger, { isLoading: isActivating, isError, data: refetchedBot, error } ] = useLazyActivateBotQuery();

  const [enableActivation, setEnableActivation] = useState(id ? true : false);

  // Activate and get bot again
  // Deals and orders information need to come from the server
  const handleActivation = async (id: string) => {
    await updateBot({ body: bot, id });
    const result = await trigger(id);
    if (!isActivating && result.data) {
      dispatch(setBot(result.data));
    }
  };
  const handlePanicSell = async (id: string) => {
    await dispatch(botsApiSlice.endpoints.deactivateBot.initiate(id));
  };

  const onSubmit = async () => {
    if (id && bot.status !== BotStatus.COMPLETED) {
      await updateBot({ body: bot, id });
      navigate(`/bots/edit/${id}`);
    } else {
      const data = await createBot(bot).unwrap();
      setEnableActivation(true);
      navigate(`/bots/edit/${data}`);
    }
  };

  useEffect(() => {
    if (isActivating) {
      setSpinner(true);
    } else {
      setSpinner(false);
    }
  }, [isActivating]);

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
            <BaseOrderTab />
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
