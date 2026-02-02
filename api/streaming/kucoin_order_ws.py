import asyncio
import logging
from pydantic import BaseModel
from typing import Callable, Optional

from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.model.client_option import ClientOptionBuilder
from kucoin_universal_sdk.model.constants import GLOBAL_API_ENDPOINT
from kucoin_universal_sdk.model.websocket_option import WebSocketClientOptionBuilder

logger = logging.getLogger(__name__)


class OrderUpdate(BaseModel):
    order_id: str
    symbol: str
    side: str  # buy / sell
    status: str  # open / match / done
    filled_qty: float
    filled_quote: float
    price: Optional[float]


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
        on_update: Callable[[OrderUpdate], None],
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.on_update = on_update
        self._running = False
        self._ws_started = False

        # Initialize KuCoin Universal SDK client
        client_option = (
            ClientOptionBuilder()
            .set_key(api_key)
            .set_secret(api_secret)
            .set_passphrase(api_passphrase)
            .set_spot_endpoint(GLOBAL_API_ENDPOINT)
            .set_websocket_client_option(WebSocketClientOptionBuilder().build())
            .build()
        )

        self.client = DefaultClient(client_option)
        ws_service = self.client.ws_service()
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

        self.private_ws.order_events(callback=self.on_order_event)
        logger.info("Subscribed to /spotMarket/tradeOrders")
        self._running = True

    def on_order_event(self, topic: str, subject: str, data: dict):
        """
        Callback for order events from KuCoin websocket.

        Args:
            topic: The topic string (e.g., "/spotMarket/tradeOrders")
            subject: The subject/event type
            data: The order event data
        """
        try:
            if not isinstance(data, dict):
                logger.warning(f"Unexpected data type: {type(data)}")
                return

            event_type = data.get("type")  # open | match | done

            order = OrderUpdate(
                order_id=data.get("orderId", ""),
                symbol=data.get("symbol", ""),
                side=data.get("side", ""),
                status=event_type or "",
                filled_qty=float(data.get("filledSize", 0) or 0),
                filled_quote=float(data.get("filledFunds", 0) or 0),
                price=float(data["price"]) if data.get("price") else None,
            )

            logger.info(
                f"Order event: {event_type} - {order.symbol} {order.side} "
                f"filled: {order.filled_qty}"
            )

            self.on_update(order)

        except Exception as e:
            logger.error(f"Error processing order event: {e}", exc_info=True)

    async def run_forever(self):
        """Keep the event loop alive while processing order updates."""
        logger.info("run_forever() started for order updates")

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.warning("run_forever: CancelledError - shutting down")
            raise
        except Exception as e:
            logger.error(f"run_forever: Unexpected error: {e}", exc_info=True)
            raise
        finally:
            logger.info("run_forever() EXITING!")
