import { Anchor, Badge, Box, Stack, Title } from "@mantine/core";
import { MarketType } from "../../utils/enums";
import { normalizePriceChangePercent } from "../../utils/gainers-losers";
import { type GainersLosersProps } from "./GainersLosers";
interface GainersLosersCardProps extends GainersLosersProps {
  title: string;
}
const GainersLosersCard = ({
  data,
  market_type,
  title,
}: GainersLosersCardProps) => {
  const getNewBotPath = (symbol: string) =>
    market_type === MarketType.FUTURES
      ? `/bots/futures/new/${symbol}`
      : `/bots/new/${symbol}`;
  return (
    <Box>
      <Title order={4}>{title}</Title>
      <Stack gap={0}>
        {data.map((x, i) => {
          const priceChangePercent = normalizePriceChangePercent(x);
          return (
            parseFloat(priceChangePercent) !== 0 && (
              <Box key={i} py="xs" className="detail-row">
                <Anchor
                  href={getNewBotPath(x.symbol)}
                  style={{
                    overflowWrap: "anywhere",
                  }}
                >
                  {x.symbol}
                </Anchor>
                <Badge
                  color={
                    parseFloat(priceChangePercent) > 0 ? "success" : "danger"
                  }
                  variant="light"
                >
                  {priceChangePercent + "%"}
                </Badge>
              </Box>
            )
          );
        })}
      </Stack>
    </Box>
  );
};
export default GainersLosersCard;
