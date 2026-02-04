import asyncio
import logging
from pybinbot import KucoinApi, OrderStatus
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.model import TransportOptionBuilder
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model.constants import (
    GLOBAL_API_ENDPOINT,
    GLOBAL_FUTURES_API_ENDPOINT,
)
from kucoin_universal_sdk.model.websocket_option import WebSocketClientOptionBuilder
from databases.crud.exchange_order_crud import ExchangeOrderTableCrud

logger = logging.getLogger(__name__)


class KucoinOrderWS:
    """
    KuCoin WebSocket client for private order updates using kucoin_universal_sdk.

    Subscribes to /spotMarket/tradeOrders topic to receive real-time order events:
    - open: Order placed
    - match: Order partially or fully filled
    - done: Order completed or canceled
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self._running = False
        self._ws_started = False
        self.kucoin_api = KucoinApi(
            key=api_key, secret=api_secret, passphrase=api_passphrase
        )

        # Build websocket option separately
        ws_option = WebSocketClientOptionBuilder().build()

        # Initialize KuCoin Universal SDK client
        http_transport_option = (
            TransportOptionBuilder()
            .set_keep_alive(True)
            .set_max_pool_size(10)
            .set_max_connection_per_pool(10)
            .build()
        )

        client_option = (
            ClientOptionBuilder()
            .set_key(api_key)
            .set_secret(api_secret)
            .set_passphrase(api_passphrase)
            .set_transport_option(http_transport_option)
            .set_spot_endpoint(GLOBAL_API_ENDPOINT)
            .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
            .set_websocket_client_option(ws_option)
            .build()
        )

        client = DefaultClient(client_option)
        ws_service = client.ws_service()
        self.private_ws = ws_service.new_spot_private_ws()

        logger.info("KuCoin Order WS initialized")

    def start(self):
        """Start the WebSocket connection."""
        logger.info("Starting KuCoin private websocket connection...")
        self.private_ws.start()
        self._ws_started = True
        logger.info("KuCoin private websocket started")

    async def subscribe_orders(self):
        """Subscribe to order updates topic."""
        if not self._ws_started:
            self.start()

        # Small delay to ensure connection is ready
        await asyncio.sleep(0.1)

        self.private_ws.order_v2(callback=self.on_order_event)
        logger.info("Subscribed to order updates")
        self._running = True

    def on_order_event(self, topic, subject, data: dict) -> None:
        """
        Callback for order events from KuCoin websocket.

        Args:
            topic: The topic string (e.g., "/spotMarket/tradeOrders")
            subject: The subject/event type
            data: The order event data
        """
        if not isinstance(data, dict):
            logger.error(f"Unexpected data type: {type(data)}")
            return

        event_type = data.get("type")  # open | match | done
        status = (
            OrderStatus.map_from_kucoin_status(event_type)
            if event_type
            else OrderStatus.FILLED
        )
        order = ExchangeOrderTableCrud().update_one(
            order_id=data["orderId"],
            price=float(data["price"]),
            filled_qty=float(data["filledSize"]),
            order_time=int(data["orderTime"]),
            status=status,
            side=data["side"],
        )

        logger.info(
            f"Order event: {event_type}"
            f"Status: {order.status}"
            f"Topic: {topic}"
            f"Subject: {subject}"
        )

    async def run_forever(self):
        """Keep the event loop alive while processing order updates."""
        logger.info("run_forever() started for order updates")
        while self._running:
            await asyncio.sleep(1)
