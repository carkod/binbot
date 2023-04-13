import json
import logging
import time
import logging
import threading
from websocket import (
    ABNF,
    create_connection,
    WebSocketException,
    WebSocketConnectionClosedException,
)


class BinanceSocketManager(threading.Thread):
    def __init__(
        self,
        stream_url,
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        logger=None,
    ):
        threading.Thread.__init__(self)
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.stream_url = stream_url
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_error = on_error
        self.create_ws_connection()
    
    def create_ws_connection(self):
        self.logger.debug(
            "Creating connection with WebSocket Server: %s", self.stream_url
        )
        self.ws = create_connection(self.stream_url)
        self.logger.debug(
            "WebSocket connection has been established: %s", self.stream_url
        )
        self._callback(self.on_open)

    def run(self):
        self.read_data()

    def send_message(self, message):
        self.logger.debug("Sending message to Binance WebSocket Server: %s", message)
        self.ws.send(message)

    def ping(self):
        self.ws.ping()

    def read_data(self):
        data = ""
        while True:
            try:
                op_code, frame = self.ws.recv_data_frame(True)
            except WebSocketException as e:
                if isinstance(e, WebSocketConnectionClosedException):
                    self.logger.error("Lost websocket connection")
                else:
                    self.logger.error("Websocket exception: {}".format(e))
                raise e
            except Exception as e:
                self.logger.error("Exception in read_data: {}".format(e))
                raise e

            if op_code == ABNF.OPCODE_CLOSE:
                self.logger.warning(
                    "CLOSE frame received, closing websocket connection"
                )
                self._callback(self.on_close)
                break
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
                self.ws.pong("")
                self.logger.debug("Received Ping; PONG frame sent back")
            elif op_code == ABNF.OPCODE_PONG:
                self.logger.debug("Received PONG frame")
                self._callback(self.on_pong)
            else:
                data = frame.data
                if op_code == ABNF.OPCODE_TEXT:
                    data = data.decode("utf-8")
                self._callback(self.on_message, data)

    def close(self):
        if not self.ws.connected:
            self.logger.warn("Websocket already closed")
        else:
            self.ws.send_close()
        return

    def _callback(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception as e:
                self.logger.error("Error from callback {}: {}".format(callback, e))
                if self.on_error:
                    self.on_error(self, e)

class BinanceWebsocketClient:
    ACTION_SUBSCRIBE = "SUBSCRIBE"
    ACTION_UNSUBSCRIBE = "UNSUBSCRIBE"

    def __init__(
        self,
        stream_url,
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        logger=None,
    ):
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.socket_manager = self._initialize_socket(
            stream_url,
            on_message,
            on_open,
            on_close,
            on_error,
            on_ping,
            on_pong,
            logger,
        )

        # start the thread
        self.socket_manager.start()
        self.logger.debug("Binance WebSocket Client started.")

    def _initialize_socket(
        self,
        stream_url,
        on_message,
        on_open,
        on_close,
        on_error,
        on_ping,
        on_pong,
        logger,
    ):
        return BinanceSocketManager(
            stream_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
            logger=logger,
        )

    def get_timestamp(self):
        return int(time.time() * 1000)

    def send(self, message: dict):
        self.socket_manager.send_message(json.dumps(message))

    def send_message_to_server(self, message, action=None, id=None):
        if not id:
            id = self.get_timestamp()

        if action != self.ACTION_UNSUBSCRIBE:
            return self.subscribe(message, id=id)
        return self.unsubscribe(message, id=id)

    def subscribe(self, stream, id=None):
        if not id:
            id = self.get_timestamp()
        if self._single_stream(stream):
            stream = [stream]
        json_msg = json.dumps({"method": "SUBSCRIBE", "params": stream, "id": id})
        self.socket_manager.send_message(json_msg)

    def unsubscribe(self, stream: str, id=None):
        if not id:
            id = self.get_timestamp()

        if not self._single_stream(stream):
            raise ValueError("Invalid stream name, expect a string")

        stream = [stream]
        self.socket_manager.send_message(
            json.dumps({"method": "UNSUBSCRIBE", "params": stream, "id": id})
        )

    def ping(self):
        self.logger.debug("Sending ping to Binance WebSocket Server")
        self.socket_manager.ping()

    def stop(self, id=None):
        self.socket_manager.close()
        self.socket_manager.join()

    def list_subscribe(self, id=None):
        """sending the list subscription message, e.g.

        {"method": "LIST_SUBSCRIPTIONS","id": 100}

        """

        if not id:
            id = self.get_timestamp()
        self.socket_manager.send_message(
            json.dumps({"method": "LIST_SUBSCRIPTIONS", "id": id})
        )

    def _single_stream(self, stream):
        if isinstance(stream, str):
            return True
        elif isinstance(stream, list):
            return False
        else:
            raise ValueError("Invalid stream name, expect string or array")
