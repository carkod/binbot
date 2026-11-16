import { Box, Card, SimpleGrid, Table, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import { useGetBalanceQuery } from "../../features/balanceApiSlice";
import { useGetAlgoRankingQuery } from "../../features/bots/botsApiSlice";
import { useGetSignalsQuery } from "../../features/signalsApiSlice";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
import CardLoadingSpinner from "../components/CardLoadingSpinner";
import { useBinquantStrategyNames } from "../hooks/useBinquantStrategyNames";
const SignalsPage = () => {
  const { data: accountData } = useGetBalanceQuery();
  const { data: algoRanking, isLoading: loadingAlgoRanking } =
    useGetAlgoRankingQuery();
  const {
    strategyNames,
    isLoading: loadingStrategyNames,
    error: strategyNamesError,
  } = useBinquantStrategyNames();
  const { data: signals, isLoading: loadingSignals } = useGetSignalsQuery({
    limit: 1000,
  });
  const filteredAlgoRanking = useMemo(
    () =>
      algoRanking?.filter(
        ({ name }) =>
          name === "terminal" || strategyNames.has(name.toLowerCase()),
      ) ?? [],
    [algoRanking, strategyNames],
  );
  const topAlgoCounts = new Set(
    filteredAlgoRanking
      .map(({ count }) => count)
      .sort((a, b) => b - a)
      .slice(0, 3),
  );
  const rankedSignalAlgorithms = useMemo(() => {
    const algorithms = new Map<
      string,
      {
        algorithm_name: string;
        generated_at: string;
        current_regime?: string | null;
        count: number;
      }
    >();
    signals?.forEach(({ algorithm_name, generated_at, current_regime }) => {
      const algorithm = algorithms.get(algorithm_name);
      if (!algorithm) {
        algorithms.set(algorithm_name, {
          algorithm_name,
          generated_at,
          current_regime,
          count: 1,
        });
        return;
      }
      algorithm.count += 1;
      if (new Date(generated_at) > new Date(algorithm.generated_at)) {
        algorithm.generated_at = generated_at;
        algorithm.current_regime = current_regime;
      }
    });
    return [...algorithms.values()].sort((left, right) => {
      const countDifference = right.count - left.count;
      if (countDifference !== 0) return countDifference;
      return (
        new Date(right.generated_at).getTime() -
        new Date(left.generated_at).getTime()
      );
    });
  }, [signals]);
  return (
    <div className="content">
      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        {(loadingAlgoRanking ||
          loadingStrategyNames ||
          strategyNamesError ||
          filteredAlgoRanking.length > 0) && (
          <Box className="signals-ranking">
            {loadingAlgoRanking || loadingStrategyNames ? (
              <CardLoadingSpinner label="strategy ranking" />
            ) : (
              <Card mb="md">
                <Box mb="sm">
                  <Title
                    order={5}
                    display="flex"
                    style={{
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Box
                      c="warning.9"
                      className="fa-solid fa-trophy"
                      component="i"
                    />
                    <span>Strategy ranking</span>
                  </Title>
                  <Text c="dimmed">
                    Strategies executed by Binquant and bots created in Terminal
                  </Text>
                </Box>
                <Box>
                  {strategyNamesError ? (
                    <Text role="alert" c="danger.8">
                      {strategyNamesError}
                    </Text>
                  ) : (
                    <Box className="table-scroll">
                      <Table highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>#</Table.Th>
                            <Table.Th>Name</Table.Th>
                            <Table.Th ta="right">Count</Table.Th>
                            <Table.Th ta="right">
                              Profit ({accountData?.fiat_currency})
                            </Table.Th>
                            <Table.Th ta="right">Performance</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {filteredAlgoRanking.map(
                            ({ name, count, bot_profit }, index) => (
                              <Table.Tr
                                key={name}
                                className={
                                  topAlgoCounts.has(count)
                                    ? "table-secondary text-white"
                                    : ""
                                }
                              >
                                <Table.Td>{index + 1}</Table.Td>
                                <Table.Td>{name}</Table.Td>
                                <Table.Td ta="right">{count}</Table.Td>
                                <Table.Td ta="right">
                                  {roundDecimals(bot_profit, 2)}%
                                </Table.Td>
                                <Table.Td ta="right">
                                  {count > 0
                                    ? ((bot_profit / count) * 100).toFixed(2) +
                                      "%"
                                    : ""}
                                </Table.Td>
                              </Table.Tr>
                            ),
                          )}
                        </Table.Tbody>
                      </Table>
                    </Box>
                  )}
                </Box>
              </Card>
            )}
          </Box>
        )}
        {(loadingSignals || rankedSignalAlgorithms.length > 0) && (
          <Box className="signals-ranking">
            {loadingSignals ? (
              <CardLoadingSpinner label="signal ranking" />
            ) : (
              <Card mb="md">
                <Box mb="sm">
                  <Title
                    order={5}
                    display="flex"
                    style={{
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Box
                      c="info.8"
                      className="fa-solid fa-signal"
                      component="i"
                    />
                    <span>Signal Ranking</span>
                  </Title>
                  <Text c="dimmed">
                    Latest strategy signals ranked by algorithm frequency
                  </Text>
                </Box>
                <Box>
                  <Box className="table-scroll">
                    <Table highlightOnHover>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Algorithm</Table.Th>
                          <Table.Th>Generated</Table.Th>
                          <Table.Th>Regime</Table.Th>
                          <Table.Th ta="right">Count</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {rankedSignalAlgorithms.map(
                          ({
                            algorithm_name,
                            generated_at,
                            current_regime,
                            count,
                          }) => (
                            <Table.Tr key={algorithm_name}>
                              <Table.Td>{algorithm_name}</Table.Td>
                              <Table.Td>
                                {formatTimestamp(generated_at)}
                              </Table.Td>
                              <Table.Td>{current_regime || "-"}</Table.Td>
                              <Table.Td ta="right">{count}</Table.Td>
                            </Table.Tr>
                          ),
                        )}
                      </Table.Tbody>
                    </Table>
                  </Box>
                </Box>
              </Card>
            )}
          </Box>
        )}
      </SimpleGrid>
    </div>
  );
};
export default SignalsPage;
