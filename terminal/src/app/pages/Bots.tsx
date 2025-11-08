import React, { useContext, useEffect, useState, type FC } from "react";
import { Badge, Button, Col, Container, Row, Stack } from "react-bootstrap";
import { useImmer } from "use-immer";
import {
  useDeactivateBotMutation,
  useDeleteBotMutation,
  useGetBotsQuery,
  useGetOneBySymbolQuery,
} from "../../features/bots/botsApiSlice";
import { weekAgo } from "../../utils/time";
import BotCard from "../components/BotCard";
import BotsActions, { BulkAction } from "../components/BotsActions";
import BotsDateFilter from "../components/BotsCalendar";
import ConfirmModal from "../components/ConfirmModal";
import { useAppDispatch } from "../hooks";
import { BotStatus } from "../../utils/enums";
import { SpinnerContext } from "../Layout";
import SymbolSearch from "../components/SymbolSearch";
import { useGetSymbolsQuery } from "../../features/symbolsApiSlice";

export const BotsPage: FC<{}> = () => {
  const dispatch = useAppDispatch();
  const currentTs = new Date().getTime();
  const oneWeekAgo = weekAgo();
  const { spinner, setSpinner } = useContext(SpinnerContext);
  const [removeBots, { isLoading: isDeleting, isSuccess: isDeleted }] =
    useDeleteBotMutation();
  const [
    deactivateBot,
    { isLoading: isDeactivating, isSuccess: isDeactivated },
  ] = useDeactivateBotMutation();

  // Component states
  const [selectedCards, selectCards] = useImmer([]);
  const [botToDelete, setBotToDelete] = useState<string | null>(null);
  const [, setDateFilterError] = useState(null);
  const [bulkActions, setBulkActions] = useState<BulkAction>(BulkAction.NONE);
  const [startDate, setStartDate] = useState(oneWeekAgo);
  const [endDate, setEndDate] = useState(currentTs);
  const [filterStatus, setFilterStatus] = useState<BotStatus>(BotStatus.ALL);
  const [symbolState, setSymbolState] = useState<string>("");

  // Fetch bots or single bot by symbol
  const {
    refetch: refetchBots,
    data: botsData,
    error: botsError,
    isFetching: isFetchingBots,
  } = useGetBotsQuery(
    {
      status: filterStatus,
      startDate,
      endDate,
    },
    { skip: Boolean(symbolState) },
  );

  const {
    refetch: refetchSymbol,
    data: symbolData,
    error: symbolError,
    isFetching: isFetchingSymbol,
  } = useGetOneBySymbolQuery(symbolState, { skip: !symbolState });

  // Unified data and refetch
  const data = symbolState
    ? {
        bots: {
          ids: symbolData?.bot ? [symbolData.bot.id] : [],
          entities: symbolData?.bot
            ? { [symbolData.bot.id]: symbolData.bot }
            : {},
        },
        totalProfit: 0,
      }
    : botsData;
  const refetch = symbolState ? refetchSymbol : refetchBots;
  const error = symbolState ? symbolError : botsError;
  const isFetching = symbolState ? isFetchingSymbol : isFetchingBots;

  // Symbols search dependencies
  const [symbolsList, setSymbolsList] = useImmer<string[]>([]);
  const { data: allSymbols, isFetching: isFetchingSymbols } =
    useGetSymbolsQuery();

  const handleSelection = (id: string) => {
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
    dispatch(() => refetch());
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
  const handleStartDate = (ts: number) => {
    setStartDate(ts);
    if (ts > endDate) {
      setDateFilterError("Start date cannot be greater than end date");
    } else {
      setDateFilterError(null);
      dispatch(() => refetch());
    }
  };
  const handleEndDate = (ts: number) => {
    setEndDate(ts);
    if (ts < startDate) {
      setDateFilterError("End date cannot be less than start date");
    } else {
      setDateFilterError(null);
      dispatch(() => refetch());
    }
  };

  /**
   * refetch will work without params
   * if we set all the states correctly before refetching (spinner, startDate, endDate, filterStatus)
   *
   */
  const handleSearchBySymbol = (e: React.ChangeEvent<HTMLInputElement>) => {
    const pair = e.target.value;
    if (pair && pair.length > 0) {
      setSymbolState(pair);
      setSpinner(true);
      setFilterStatus(BotStatus.ALL);
      // beginning of time
      setStartDate(new Date("1970-01-01").getTime());
      // tomorrow
      setEndDate(new Date(Date.now() + 24 * 60 * 60 * 1000).getTime());
      dispatch(() => refetch());
      setSpinner(false);
    }
  };

  useEffect(() => {
    if (isFetching || isDeactivating || isDeleting) {
      setSpinner(true);
    }
    if (data?.bots || isDeleted || isDeactivated) {
      setSpinner(false);
    }

    // Get symbols for symbol search field
    if (isFetchingSymbols) {
      setSpinner(true);
    }

    if (allSymbols?.length > 0 && !isFetchingSymbols) {
      setSpinner(false);
      const pairs = allSymbols.map((symbol) => symbol.id);
      setSymbolsList(pairs);
    }
  }, [
    data?.bots?.ids,
    dispatch,
    isFetching,
    startDate,
    filterStatus,
    endDate,
    isDeactivating,
    isDeleting,
    isDeleted,
    isDeactivated,
    allSymbols,
    isFetchingSymbols,
  ]);

  return (
    <SpinnerContext.Provider value={{ spinner, setSpinner }}>
      <Container fluid>
        <div className="mb-3 d-flex flex-column flex-lg-row justify-content-between align-items-center">
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
          <div id="filters" className="mx-3 d-flex flex-column flex-md-row">
            <Stack
              direction="horizontal"
              className="mx-3 d-flex flex-column flex-md-row mt-3 mt-md-0"
            >
              <SymbolSearch
                name="pair"
                options={symbolsList}
                defaultValue=""
                placeholder="Search by pair"
                onBlur={handleSearchBySymbol}
              />
            </Stack>
            <Stack
              direction="horizontal"
              className="mx-3 d-flex flex-column flex-md-row"
            >
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
            </Stack>
            <Stack
              direction="horizontal"
              className="mx-3 d-flex flex-column flex-md-row"
            >
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
        </div>
        <Row md="3" xs="1" lg="4">
          {data?.bots?.ids.length > 0
            ? Object.values(data.bots?.entities).map((x, i) => (
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
    </SpinnerContext.Provider>
  );
};

export default BotsPage;
