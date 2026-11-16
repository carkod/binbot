import { Text } from "@mantine/core";
import { useCvdSymbolQuery } from "../../features/marketApiSlice";
import StoredCvdCard from "./StoredCvdCard";
const SymbolCvdCard = ({
  symbol,
  enabled,
}: {
  symbol: string;
  enabled: boolean;
}) => {
  const { currentData, isFetching, isError } = useCvdSymbolQuery(symbol, {
    skip: !enabled || !symbol,
    pollingInterval: 30000,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  if (!enabled || !symbol) {
    return <Text>Enter a symbol</Text>;
  }
  return (
    <StoredCvdCard
      embedded
      symbol={symbol}
      result={currentData}
      isLoading={!currentData && isFetching}
      isError={isError}
    />
  );
};
export default SymbolCvdCard;
