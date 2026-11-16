import {
  Badge,
  Box,
  Button,
  Grid,
  Group,
  NativeSelect,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useContext, useEffect, useMemo, useState, type FC } from "react";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import {
  calculateLevelPnlSum,
  GridLadderStatus,
  isActiveGridLadder,
  type GridLadder,
} from "../../features/gridLadders/gridLadders";
import {
  useCloseGridLadderMutation,
  useDeleteGridLadderMutation,
  useGetGridLaddersQuery,
} from "../../features/gridLadders/gridLaddersApiSlice";
import { calculateGridReturnPct } from "../../utils/grid-ladder";
import { weekAgo } from "../../utils/time";
import BotsDateFilter from "../components/BotsCalendar";
import ConfirmModal from "../components/ConfirmModal";
import GridLadderCard from "../components/GridLadderCard";
import { SpinnerContext } from "../spinner-context";
const GridLaddersPage: FC = () => {
  const { setSpinner } = useContext(SpinnerContext);
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [ladderToClose, setLadderToClose] = useState<string | null>(null);
  const [ladderToDelete, setLadderToDelete] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [symbolState, setSymbolState] = useState<string>("");
  const [startDate, setStartDate] = useState<number>(weekAgo());
  const [endDate, setEndDate] = useState<number>(new Date().getTime());
  const {
    data: allLadders = [],
    isFetching,
    refetch,
  } = useGetGridLaddersQuery(
    { limit: 100, offset: 0, startDate, endDate },
    { refetchOnFocus: true },
  );
  const { data: autotradeSettings } = useGetSettingsQuery();
  const [closeGridLadder, { isLoading: isClosing }] =
    useCloseGridLadderMutation();
  const [deleteGridLadder, { isLoading: isDeleting }] =
    useDeleteGridLadderMutation();
  const fiat = autotradeSettings?.fiat ?? "fiat";
  const filteredLadders = useMemo(() => {
    return allLadders.filter((ladder) => {
      const statusMatches =
        filterStatus === "all" || ladder.status === filterStatus;
      const symbolMatches =
        !symbolState ||
        ladder.symbol.toLowerCase().includes(symbolState.toLowerCase());
      return statusMatches && symbolMatches;
    });
  }, [allLadders, filterStatus, symbolState]);
  const summary = useMemo(() => {
    return filteredLadders.reduce(
      (acc, ladder) => {
        acc.active += isActiveGridLadder(ladder.status) ? 1 : 0;
        acc.reserved += ladder.reserved_margin;
        acc.used += ladder.used_margin;
        // Active ladders keep realized_pnl=0 until close; surface TP-cycle
        // profits from individual levels so the summary isn't misleadingly 0.
        const levelPnl = isActiveGridLadder(ladder.status)
          ? calculateLevelPnlSum(ladder)
          : 0;
        acc.realized += ladder.realized_pnl + levelPnl;
        acc.unrealized += ladder.unrealized_pnl;
        acc.openLevels += ladder.levels.filter(
          (level) => level.entry_order_id || level.take_profit_order_id,
        ).length;
        return acc;
      },
      {
        active: 0,
        reserved: 0,
        used: 0,
        realized: 0,
        unrealized: 0,
        openLevels: 0,
      },
    );
  }, [filteredLadders]);
  useEffect(() => {
    setSpinner(isFetching || isClosing || isDeleting);
  }, [isFetching, isClosing, isDeleting, setSpinner]);
  const handleSelect = (id: string) => {
    setSelectedCards((prev) =>
      prev.includes(id)
        ? prev.filter((cardId) => cardId !== id)
        : prev.concat(id),
    );
  };
  const confirmDelete = async (action: number) => {
    if (action !== 1 || !ladderToDelete) {
      setLadderToDelete(null);
      return;
    }
    // Capture id and clear state immediately so the modal closes before the
    // request completes (and even if unwrap() throws).
    const id = ladderToDelete;
    setLadderToDelete(null);
    try {
      await deleteGridLadder(id).unwrap();
    } finally {
      // invalidatesTags handles cache, but refetch ensures the list updates
      // even if the tag subscription has a timing gap.
      await refetch();
    }
  };
  const confirmClose = async (action: number) => {
    if (action !== 1 || !ladderToClose) {
      setLadderToClose(null);
      return;
    }
    await closeGridLadder({
      id: ladderToClose,
      reason: "manual_close",
    }).unwrap();
    setSelectedCards([]);
    setLadderToClose(null);
    await refetch();
  };
  return (
    <Box w="100%">
      <Group
        gap={4}
        wrap="wrap"
        style={{
          flexWrap: "wrap",
        }}
      >
        <Title order={4}>
          <Badge
            color={summary.realized >= 0 ? "success" : "danger"}
            variant="light"
          >
            Realized PnL: {summary.realized.toFixed(4)}
          </Badge>
        </Title>
        <Title order={4}>
          <Badge
            color={summary.unrealized >= 0 ? "success" : "danger"}
            variant="light"
          >
            Unrealized PnL: {summary.unrealized.toFixed(4)}
          </Badge>
        </Title>
        <Title order={4}>
          <Badge color="success" variant="light">
            Active ladders: {summary.active} / 3
          </Badge>
        </Title>
        <Title order={4}>
          <Badge color="secondary" variant="light">
            Reserved margin: {summary.reserved.toFixed(2)} {fiat}
          </Badge>
        </Title>
        <Title order={4}>
          <Badge color="secondary" variant="light">
            Used margin: {summary.used.toFixed(2)} {fiat}
          </Badge>
        </Title>
        <Title order={4}>
          <Badge color="info" variant="light">
            Open levels: {summary.openLevels}
          </Badge>
        </Title>
      </Group>

      <hr />

      <Grid
        mb={16}
        gap={16}
        style={{
          alignItems: "flex-end",
        }}
      >
        <Grid.Col
          span={{
            base: 12,
            md: 2,
          }}
        >
          <TextInput
            placeholder="Search by symbol"
            value={symbolState}
            onChange={(e) => setSymbolState(e.target.value)}
          />
        </Grid.Col>
        <Grid.Col
          span={{
            base: 12,
            md: 2,
          }}
        >
          <NativeSelect
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All statuses</option>
            {Object.values(GridLadderStatus).map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </NativeSelect>
        </Grid.Col>
        <Grid.Col
          span={{
            base: 12,
            md: 2,
          }}
        >
          <BotsDateFilter
            title="Start date"
            controlId="gridStartDate"
            selectedDate={startDate}
            handleDateChange={setStartDate}
          />
        </Grid.Col>
        <Grid.Col
          span={{
            base: 12,
            md: 2,
          }}
        >
          <BotsDateFilter
            title="End date"
            controlId="gridEndDate"
            selectedDate={endDate}
            handleDateChange={setEndDate}
          />
        </Grid.Col>
        <Grid.Col
          span={{
            base: 12,
            md: "content",
          }}
        >
          <Button
            onClick={() =>
              setSelectedCards(
                filteredLadders.map((ladder: GridLadder) => ladder.id),
              )
            }
            variant="outline"
            color="secondary"
            type="button"
          >
            Select all
          </Button>{" "}
          <Button
            onClick={() => setSelectedCards([])}
            variant="outline"
            color="secondary"
            type="button"
          >
            Unselect all
          </Button>
        </Grid.Col>
      </Grid>

      <hr />

      {filteredLadders.length === 0 ? (
        <Text>No grid ladders deployed yet</Text>
      ) : (
        <Grid>
          {filteredLadders.map((ladder) => {
            const gridReturnPct = calculateGridReturnPct(ladder);
            return (
              <Grid.Col
                key={ladder.id}
                span={{
                  base: 12,
                  lg: 4,
                }}
                mb={16}
              >
                <GridLadderCard
                  ladder={ladder}
                  gridReturnPct={gridReturnPct}
                  selected={selectedCards.includes(ladder.id)}
                  onSelect={handleSelect}
                  onClose={setLadderToClose}
                  onDelete={setLadderToDelete}
                />
              </Grid.Col>
            );
          })}
        </Grid>
      )}

      <ConfirmModal
        show={Boolean(ladderToClose)}
        onClose={() => setLadderToClose(null)}
        handleActions={confirmClose}
        primary="Close ladder"
      >
        Closing a grid ladder should cancel open grid orders and stop the
        ladder. If positions are open, backend close behavior depends on the
        grid manager state.
      </ConfirmModal>

      <ConfirmModal
        show={Boolean(ladderToDelete)}
        onClose={() => setLadderToDelete(null)}
        handleActions={confirmDelete}
        primary="Delete record"
      >
        This permanently deletes the ladder record and all associated levels and
        orders from the database. It does not cancel exchange orders or close
        positions. Any active exchange activity will continue without this
        ladder record.
      </ConfirmModal>
    </Box>
  );
};
export default GridLaddersPage;
