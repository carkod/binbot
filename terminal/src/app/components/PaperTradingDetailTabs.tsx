import React, { useEffect, useState, type FC } from "react";
import { Button, Col, Nav, Row, Tab } from "react-bootstrap";
import { useNavigate, useParams } from "react-router";
import { useLazyActivateBotQuery } from "../../features/bots/botsApiSlice";
import {
  papertradingApiSlice,
  useCreateTestBotMutation,
  useEditTestBotMutation,
  useLazyActivateTestBotQuery,
} from "../../features/bots/paperTradingApiSlice";
import {
  selectTestBot,
  setTestBot,
} from "../../features/bots/paperTradingSlice";
import { setSpinner } from "../../features/layoutSlice";
import { BotStatus, BotType, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import BaseOrderTab from "./BaseOrderTab";
import StopLossTab from "./StopLossTab";
import TakeProfit from "./TakeProfitTab";

const PaperTradingDetailTabs: FC = () => {
  const { paperTrading } = useAppSelector(selectTestBot);
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [updateBot] = useEditTestBotMutation();
  const [createBot] = useCreateTestBotMutation();
  const [
    trigger,
    { isLoading: isActivating, isError, data: refetchedBot, error },
  ] = useLazyActivateTestBotQuery();

  const [enableActivation, setEnableActivation] = useState(id ? true : false);

  // Activate and get bot again
  // Deals and orders information need to come from the server
  const handleActivation = async (id: string) => {
    await updateBot({ body: paperTrading, id });
    const result = await trigger(id);
    if (!isActivating && result.data) {
      navigate(`/paper-trading/edit/${id}`);
    }
  };
  const handlePanicSell = async (id: string) => {
    await dispatch(
      papertradingApiSlice.endpoints.deactivateTestBot.initiate(id)
    );
  };

  const onSubmit = async () => {
    if (id && paperTrading.status !== BotStatus.COMPLETED) {
      const submitData = {
        ...paperTrading,
        deal: undefined,
        orders: undefined,
      }
      await updateBot({ body: submitData, id });
      navigate(`/paper-trading/edit/${id}`);
    } else {
      const submitData = { ...paperTrading, id: undefined };
      await createBot(submitData);
      setEnableActivation(true);
      navigate(`/paper-trading/edit/${id}`);
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
            <BaseOrderTab botType={BotType.PAPER_TRADING} />
            <StopLossTab botType={BotType.PAPER_TRADING} />
            <TakeProfit botType={BotType.PAPER_TRADING} />
          </Tab.Content>
        </Col>
      </Row>
      <Row>
        <Col lg="3">
          {paperTrading?.status !== BotStatus.COMPLETED && (
            <Button
              className="btn-round"
              color="primary"
              onClick={() => {
                handleActivation(paperTrading.id);
              }}
              disabled={!enableActivation}
            >
              {paperTrading.status === BotStatus.ACTIVE &&
              Object.keys(paperTrading.deal).length > 0
                ? "Update deal"
                : "Deal"}
            </Button>
          )}
        </Col>
        <Col lg="3">
          {paperTrading.status === BotStatus.ACTIVE &&
            Object.keys(paperTrading.deal).length > 0 && (
              <Button
                className="btn-round"
                color="primary"
                onClick={() => handlePanicSell(paperTrading.id)}
              >
                Panic close
              </Button>
            )}
        </Col>
        <Col lg="3">
          {(paperTrading.status !== BotStatus.ACTIVE ||
            Object.keys(paperTrading.deal).length === 0) && (
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

export default PaperTradingDetailTabs;
