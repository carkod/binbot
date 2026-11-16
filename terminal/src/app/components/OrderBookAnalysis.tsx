import { Alert, SimpleGrid } from "@mantine/core";
import { getApiErrorMessage } from "../../utils/api";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import SpreadAndDepthCard from "./SpreadAndDepthCard";
import SymbolCvdCard from "./SymbolCvdCard";
const OrderBookAnalysis = ({
  enabled,
  showError = false,
}: {
  enabled: boolean;
  showError?: boolean;
}) => {
  const { symbol, liquidity, orderBookHistory } = useMicrostructureData();
  const { isFetching, isError, error, refetch } = liquidity;
  return (
    <>
      {enabled && showError && isError && (
        <Alert color="danger">
          {getApiErrorMessage(error, "KuCoin symbol request failed")}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <SpreadAndDepthCard
          orderBookHistory={orderBookHistory}
          enabled={enabled}
          isFetching={isFetching}
          isError={isError}
          onRetry={() => refetch()}
        />
        <SymbolCvdCard symbol={symbol} enabled={enabled} />
      </SimpleGrid>
    </>
  );
};
export default OrderBookAnalysis;
