import { useState, type FC } from "react";
import { Button, Col, Nav, Row, Tab } from "react-bootstrap";
import { selectBot, setBot } from "../../features/bots/botSlice";
import { BotStatus, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import BaseOrderTab from "./BaseOrderTab";
import StopLossTab from "./StopLossTab";
import TakeProfit from "./TakeProfitTab";
import {
  botsApiSlice,
  useCreateBotMutation,
  useEditBotMutation,
} from "../../features/bots/botsApiSlice";
import { useNavigate, useParams } from "react-router";

const BotDetailTabs: FC = () => {
  const { bot } = useAppSelector(selectBot);
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [updateBot] = useEditBotMutation();

  const [createBot] = useCreateBotMutation();

  const [enableActivation, setEnableActivation] = useState(id ? true : false);

  // Activate and get bot again
  // Deals and orders information need to come from the server
  const handleActivation = (id: string) => {
    const response = dispatch(botsApiSlice.endpoints.activateBot.initiate(id));
    console.log("Activate bot", response);
    dispatch(botsApiSlice.endpoints.getSingleBot.initiate(id));
  };
  const handlePanicSell = (id: string) => {
    console.log("Panic sell", id);
  };

  const onSubmit = async () => {
    let response;
    if (id && bot.status !== BotStatus.COMPLETED) {
      response = await updateBot({ body: bot, id }).unwrap();
    } else {
      response = await createBot(bot).unwrap();
    }

    let botId = id;
    if (response?.botId) {
      botId = response.botId;
    }

    setEnableActivation(true);
    navigate(`/bots/edit/${botId}`);
  };

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
              onClick={() => handleActivation(bot.id)}
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
