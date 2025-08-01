import React, { useContext, useEffect, useState, type FC } from "react";
import { Badge, Button, Col, Container, Row, Stack } from "react-bootstrap";
import { useNavigate } from "react-router";
import { useImmer } from "use-immer";
import {
  papertradingApiSlice,
  useDeactivateTestBotMutation,
  useDeleteTestBotMutation,
  useGetTestBotsQuery,
} from "../../features/bots/paperTradingApiSlice";
import { SpinnerContext } from "../Layout";
import { weekAgo } from "../../utils/time";
import BotCard from "../components/BotCard";
import BotsActions, { BulkAction } from "../components/BotsActions";
import BotsDateFilter from "../components/BotsCalendar";
import ConfirmModal from "../components/ConfirmModal";
import { useAppDispatch } from "../hooks";
import { BotStatus } from "../../utils/enums";

export const PaperTradingPage: FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const currentTs = new Date().getTime();
  const oneWeekAgo = weekAgo();
  const { spinner, setSpinner } = useContext(SpinnerContext);
  const [removeBots, { isLoading: isDeleting, isSuccess: isDeleted }] =
    useDeleteTestBotMutation();
  const [
    deactivateBot,
    { isLoading: isDeactivating, isSuccess: isDeactivated },
  ] = useDeactivateTestBotMutation();

  // Component states
  const [selectedCards, selectCards] = useImmer([]);
  const [botToDelete, setBotToDelete] = useState<string | null>(null);
  const [dateFilterError, setDateFilterError] = useState(null);
  const [bulkActions, setBulkActions] = useState<BulkAction>(BulkAction.NONE);
  const [startDate, setStartDate] = useState(oneWeekAgo);
  const [endDate, setEndDate] = useState(currentTs);
  const [filterStatus, setFilterStatus] = useState<BotStatus>(BotStatus.ALL);

  const { refetch, data, isFetching } = useGetTestBotsQuery({
    status: filterStatus,
    startDate,
    endDate,
  });

  const handleSelection = (id) => {
    let newCards = [];
    if (selectedCards.includes(id)) {
      newCards = selectedCards.filter((x) => x !== id);
    } else {
      newCards = selectedCards.concat(id);
    }
    selectCards(newCards);
  };
  const handleDelete = (botId: string) => {
    setBotToDelete(botId);
  };
  const confirmDelete = (index) => {
    if (index === 1) {
      removeBots([botToDelete]);
    } else if (index === 2) {
      deactivateBot(botToDelete);
    }
    setBotToDelete(null);
    return false;
  };
  const onSubmitBulkAction = () => {
    switch (bulkActions) {
      case BulkAction.DELETE:
        removeBots(selectedCards);
        selectCards([]);
        dispatch(() => refetch());
        break;
      case BulkAction.SELECT_ALL:
        if (data?.bots?.ids.length > 0) {
          selectCards(Object.keys(data.bots.entities));
        }
        break;
      case BulkAction.COMPLETED:
        setBulkActions(BulkAction.COMPLETED);
        setFilterStatus(BotStatus.COMPLETED);
        break;
      case BulkAction.ACTIVE:
        setBulkActions(BulkAction.ACTIVE);
        setFilterStatus(BotStatus.ACTIVE);
        break;
      case BulkAction.UNSELECT_ALL:
        selectCards([]);
        break;
      default:
        break;
    }
  };
  const handleStartDate = (ts) => {
    setStartDate(ts);
    if (ts > endDate) {
      setDateFilterError("Start date cannot be greater than end date");
    } else {
      setDateFilterError(null);
      dispatch(
        papertradingApiSlice.endpoints.getTestBots.initiate({
          status: filterStatus,
          startDate: ts,
          endDate: endDate,
        }),
      );
    }
  };
  const handleEndDate = (ts) => {
    setEndDate(ts);
    if (ts < startDate) {
      setDateFilterError("End date cannot be less than start date");
    } else {
      setDateFilterError(null);
      dispatch(() => refetch());
    }
  };

  useEffect(() => {
    if (isFetching || isDeactivating || isDeleting) {
      setSpinner(true);
    }
    if (data?.bots || isDeactivated || isDeleted) {
      setSpinner(false);
    }
  }, [
    data?.bots?.ids,
    dispatch,
    isFetching,
    isDeactivating,
    isDeleting,
    isDeactivated,
    isDeleted,
  ]);

  return (
    <Container fluid>
      <Stack
        direction="horizontal"
        className="mb-3 d-flex flex-row justify-content-between"
      >
        <div id="bot-profits">
          <h4>
            {data?.bots?.ids.length > 0 && (
              <Badge bg={data.totalProfit > 0 ? "success" : "danger"}>
                <i className="fas fa-building-columns" />{" "}
                <span className="visually-hidden">Profit</span>
                {(data.totalProfit || 0) + "%"}
              </Badge>
            )}
          </h4>
        </div>
        <div id="filters">
          <Stack direction="horizontal">
            <div className="p-3">
              <BotsActions
                defaultValue={bulkActions}
                handleChange={(e) =>
                  setBulkActions(e.target.value as BulkAction)
                }
              />
            </div>
            <div className="p-3">
              <Button onClick={onSubmitBulkAction}>Apply bulk action</Button>
            </div>
            <div className="p-3">
              <BotsDateFilter
                title="Filter by start date"
                controlId="startDate"
                selectedDate={startDate}
                handleDateChange={handleStartDate}
              />
            </div>
            <div className="p-3">
              <BotsDateFilter
                title="Filter by end date"
                controlId="endDate"
                selectedDate={endDate}
                handleDateChange={handleEndDate}
              />
            </div>
          </Stack>
        </div>
      </Stack>
      <Row md="4">
        {data?.bots?.ids.length > 0
          ? Object.values(data?.bots?.entities).map((x, i) => (
              <Col key={i}>
                <BotCard
                  botIndex={i}
                  bot={x}
                  selectedCards={selectedCards}
                  handleDelete={handleDelete}
                  handleSelection={handleSelection}
                />
              </Col>
            ))
          : ""}
      </Row>
      <ConfirmModal
        show={!!botToDelete}
        handleActions={confirmDelete}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <span className="visually-hidden">Delete</span>
          </>
        }
        secondary={
          <>
            <i className="fa-solid fa-power-off" />
            <span title="Deactivate" className="visually-hidden">
              Deactivate
            </span>
          </>
        }
      >
        To close orders, please deactivate. Deleting will only remove the bot.
      </ConfirmModal>
    </Container>
  );
};

export default PaperTradingPage;
