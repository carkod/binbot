import {
  Badge,
  Box,
  Button,
  Flex,
  SimpleGrid,
  VisuallyHidden,
} from "@mantine/core";
import React, { useContext, useEffect, useState, type FC } from "react";
import { useImmer } from "use-immer";
import {
  useDeactivateBotMutation,
  useDeleteBotMutation,
  useGetBotsQuery,
  useGetOneBySymbolQuery,
} from "../../features/bots/botsApiSlice";
import { useGetSymbolsQuery } from "../../features/symbolsApiSlice";
import { BotStatus } from "../../utils/enums";
import { weekAgo } from "../../utils/time";
import BotCard from "../components/BotCard";
import BotsActions, { BulkAction } from "../components/BotsActions";
import BotsDateFilter from "../components/BotsCalendar";
import ConfirmModal from "../components/ConfirmModal";
import SymbolSearch from "../components/SymbolSearch";
import { useAppDispatch } from "../hooks";
import { SpinnerContext } from "../spinner-context";
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
    isFetching: isFetchingBots,
  } = useGetBotsQuery(
    {
      status: filterStatus,
      startDate,
      endDate,
    },
    {
      refetchOnFocus: true,
    },
  );
  const {
    refetch: refetchSymbol,
    data: symbolData,
    isFetching: isFetchingSymbol,
  } = useGetOneBySymbolQuery(symbolState, {
    skip: !symbolState,
    refetchOnFocus: true,
  });
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
  const isFetching = symbolState ? isFetchingSymbol : isFetchingBots;
  // Symbols search dependencies
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
  const confirmDelete = async (index) => {
    if (index === 1) {
      await removeBots([botToDelete]).unwrap();
      setBotToDelete(null);
      await refetchBots();
    } else if (index === 2) {
      await deactivateBot(botToDelete).unwrap();
      setBotToDelete(null);
      await refetchBots();
    } else {
      setBotToDelete(null);
    }
    return false;
  };
  const onSubmitBulkAction = async () => {
    switch (bulkActions) {
      case BulkAction.DELETE:
        await removeBots(selectedCards).unwrap();
        selectCards([]);
        await refetchBots();
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
      <Box w="100%">
        <Flex
          direction={{ base: "column", xl: "row" }}
          gap="md"
          align={{ base: "stretch", xl: "end" }}
          justify="space-between"
          mb="lg"
        >
          <Box id="bot-profits">
            {data?.bots?.ids.length > 0 && (
              <Badge
                size="lg"
                title="Average price return of closed bots in this list"
                color={data.totalProfit > 0 ? "success" : "danger"}
              >
                <VisuallyHidden>Average closed-bot return</VisuallyHidden>
                {(data.totalProfit || 0) + "%"}
              </Badge>
            )}
          </Box>
          <Flex id="filters" wrap="wrap" gap="md" align="end">
            <Box flex="1 1 180px">
              <SymbolSearch
                name="pair"
                placeholder="Search by pair"
                onBlur={handleSearchBySymbol}
              />
            </Box>
            <BotsActions
              defaultValue={bulkActions}
              handleChange={(e) => setBulkActions(e.target.value as BulkAction)}
            />
            <Button onClick={onSubmitBulkAction} mb="sm">
              Apply bulk action
            </Button>
            <BotsDateFilter
              title="Filter by start date"
              controlId="startDate"
              selectedDate={startDate}
              handleDateChange={handleStartDate}
            />
            <BotsDateFilter
              title="Filter by end date"
              controlId="endDate"
              selectedDate={endDate}
              handleDateChange={handleEndDate}
            />
          </Flex>
        </Flex>
        <SimpleGrid cols={{ base: 1, md: 3, lg: 4 }}>
          {data?.bots?.ids.length > 0
            ? Object.values(data.bots?.entities).map((x, i) => (
                <Box key={i}>
                  <BotCard
                    botIndex={i}
                    bot={x}
                    selectedCards={selectedCards}
                    handleDelete={handleDelete}
                    handleSelection={handleSelection}
                  />
                </Box>
              ))
            : ""}
        </SimpleGrid>
        <ConfirmModal
          show={!!botToDelete}
          onClose={() => setBotToDelete(null)}
          handleActions={confirmDelete}
          primary={
            <>
              <i className="fa-solid fa-trash" />
              <VisuallyHidden>Delete</VisuallyHidden>
            </>
          }
          secondary={
            <>
              <i className="fa-solid fa-power-off" />
              <VisuallyHidden title="Deactivate">Deactivate</VisuallyHidden>
            </>
          }
        >
          To close orders, please deactivate. Deleting will only remove the bot.
        </ConfirmModal>
      </Box>
    </SpinnerContext.Provider>
  );
};
export default BotsPage;
