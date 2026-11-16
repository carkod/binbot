import {
  Badge,
  Box,
  Button,
  Card,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { useState } from "react";
import type { Bot } from "../../features/bots/botInitialState";
import { formatTimestamp, renderDuration } from "../../utils/time";
interface BotInfoProps {
  bot: Bot;
}
export default function BotInfo({ bot }: BotInfoProps) {
  const [isExpanded, setExpanded] = useState<boolean>(bot.orders?.length > 0);
  return (
    <Tabs
      defaultValue="orders"
      keepMounted={false}
      keepMountedMode="display-none"
    >
      <Card mb="md">
        <Box
          mb="sm"
          display="flex"
          style={{
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Title order={5}>Bot information</Title>
          <Button
            onClick={() => setExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            type="button"
          >
            {isExpanded ? "Hide" : "Show"}
          </Button>
        </Box>
        {isExpanded && (
          <Box>
            <Tabs.List>
              <>
                <Tabs.Tab value="orders">Orders information</Tabs.Tab>
              </>
              <>
                <Tabs.Tab value="deal">Deal information</Tabs.Tab>
              </>
            </Tabs.List>
            <Box>
              <Tabs.Panel value="orders" pt="md">
                {bot.orders.length > 0 && (
                  <Box className="table-scroll">
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Order Id</Table.Th>
                          <Table.Th>Timestamp</Table.Th>
                          <Table.Th>Deal type</Table.Th>
                          <Table.Th>Order type</Table.Th>
                          <Table.Th>Price</Table.Th>
                          <Table.Th>Qty</Table.Th>
                          <Table.Th>Status</Table.Th>
                          <Table.Th>Order Side</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {bot.orders.map((order, i) => {
                          if (
                            typeof order === "object" &&
                            "order_type" in order
                          ) {
                            return (
                              <Table.Tr key={order.order_id}>
                                <Table.Th scope="row">
                                  {order.order_id}
                                </Table.Th>
                                <Table.Td>
                                  {formatTimestamp(parseFloat(order.timestamp))}
                                </Table.Td>
                                <Table.Td>{order.deal_type}</Table.Td>
                                <Table.Td>{order.order_type}</Table.Td>
                                <Table.Td>{order.price}</Table.Td>
                                <Table.Td>{parseFloat(order.qty)}</Table.Td>
                                <Table.Td>{order.status}</Table.Td>
                                <Table.Td>{order.order_side}</Table.Td>
                              </Table.Tr>
                            );
                          }
                          return (
                            <Table.Tr key={i}>
                              <Table.Td></Table.Td>
                            </Table.Tr>
                          );
                        })}
                      </Table.Tbody>
                    </Table>
                  </Box>
                )}
              </Tabs.Panel>
              <Tabs.Panel value="deal" pt="md">
                {bot.deal && (
                  <Box w="100%">
                    <footer>
                      <Text>Represented in the chart</Text>
                    </footer>
                    <Stack gap={0}>
                      {Object.keys(bot.deal)
                        .filter((k) => k !== "conditional_close_order")
                        .map((k, i) => {
                          let dealData = bot.deal[k];
                          if (
                            k === "opening_timestamp" ||
                            k === "closing_timestamp"
                          ) {
                            dealData =
                              bot.deal[k] === 0 || formatTimestamp(bot.deal[k]);
                          }
                          if (
                            dealData !== null &&
                            typeof dealData === "object"
                          ) {
                            dealData = JSON.stringify(dealData);
                          }
                          return (
                            <Box key={i} className="detail-row">
                              <Text component="span" size="xs">
                                {k}
                              </Text>
                              {dealData || dealData > 0 ? (
                                <Badge color="secondary" variant="light">
                                  {dealData}
                                </Badge>
                              ) : (
                                <Text component="span" size="xs">
                                  {dealData}
                                </Text>
                              )}
                            </Box>
                          );
                        })}
                      <Box className="detail-row">
                        <Text component="span" size="xs">
                          deal duration
                        </Text>
                        <Badge color="secondary" variant="light">
                          {renderDuration(bot)}
                        </Badge>
                      </Box>
                    </Stack>
                  </Box>
                )}
              </Tabs.Panel>
            </Box>
          </Box>
        )}
      </Card>
    </Tabs>
  );
}
