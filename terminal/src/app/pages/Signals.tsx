import { useMemo } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import { useGetBalanceQuery } from "../../features/balanceApiSlice";
import { useGetAlgoRankingQuery } from "../../features/bots/botsApiSlice";
import { useGetSignalsQuery } from "../../features/signalsApiSlice";
import { roundDecimals } from "../../utils/math";
import { formatTimestamp } from "../../utils/time";
import { useBinquantStrategyNames } from "../hooks/useBinquantStrategyNames";
import CardLoadingSpinner from "../components/CardLoadingSpinner";

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
      <Row>
        {(loadingAlgoRanking ||
          loadingStrategyNames ||
          strategyNamesError ||
          filteredAlgoRanking.length > 0) && (
          <Col lg="6" md="12" className="signals-ranking">
            {loadingAlgoRanking || loadingStrategyNames ? (
              <CardLoadingSpinner label="strategy ranking" />
            ) : (
              <Card>
                <Card.Header>
                  <Card.Title
                    as="h5"
                    className="d-flex align-items-center gap-2"
                  >
                    <i className="fa-solid fa-trophy text-warning" />
                    <span>Strategy ranking</span>
                  </Card.Title>
                  <Card.Text className="text-body-secondary">
                    Strategies executed by Binquant and bots created in Terminal
                  </Card.Text>
                </Card.Header>
                <Card.Body>
                  {strategyNamesError ? (
                    <p className="text-danger" role="alert">
                      {strategyNamesError}
                    </p>
                  ) : (
                    <Table hover responsive size="sm">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Name</th>
                          <th className="text-end">Count</th>
                          <th className="text-end">
                            Profit ({accountData?.fiat_currency})
                          </th>
                          <th className="text-end">Performance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredAlgoRanking.map(
                          ({ name, count, bot_profit }, index) => (
                            <tr
                              key={name}
                              className={
                                topAlgoCounts.has(count)
                                  ? "table-secondary text-white"
                                  : ""
                              }
                            >
                              <td>{index + 1}</td>
                              <td>{name}</td>
                              <td className="text-end">{count}</td>
                              <td className="text-end">
                                {roundDecimals(bot_profit, 2)}%
                              </td>
                              <td className="text-end">
                                {count > 0
                                  ? ((bot_profit / count) * 100).toFixed(2) +
                                    "%"
                                  : ""}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>
        )}
        {(loadingSignals || rankedSignalAlgorithms.length > 0) && (
          <Col lg="6" md="12" className="signals-ranking">
            {loadingSignals ? (
              <CardLoadingSpinner label="signal ranking" />
            ) : (
              <Card>
                <Card.Header>
                  <Card.Title
                    as="h5"
                    className="d-flex align-items-center gap-2"
                  >
                    <i className="fa-solid fa-signal text-info" />
                    <span>Signal Ranking</span>
                  </Card.Title>
                  <Card.Text className="text-body-secondary">
                    Latest strategy signals ranked by algorithm frequency
                  </Card.Text>
                </Card.Header>
                <Card.Body>
                  <Table hover responsive size="sm">
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>Generated</th>
                        <th>Regime</th>
                        <th className="text-end">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rankedSignalAlgorithms.map(
                        ({
                          algorithm_name,
                          generated_at,
                          current_regime,
                          count,
                        }) => (
                          <tr key={algorithm_name}>
                            <td>{algorithm_name}</td>
                            <td>{formatTimestamp(generated_at)}</td>
                            <td>{current_regime || "-"}</td>
                            <td className="text-end">{count}</td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </Table>
                </Card.Body>
              </Card>
            )}
          </Col>
        )}
      </Row>
    </div>
  );
};

export default SignalsPage;
