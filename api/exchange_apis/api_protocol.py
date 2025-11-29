from typing import Protocol, Any


class ExchangeApiProtocol(Protocol):
    """
    Minimal shared protocol used generically by controllers across exchanges.
    """

    def get_server_time(self) -> Any: ...
    def get_order(self, order_id: str) -> dict: ...
    def add_order(
        self,
        symbol: str,
        side: Any,
        order_type: Any,
        size: float,
        price: float = 0,
        time_in_force: Any = ...,
    ) -> Any: ...
    def cancel_order(self, order_id: str) -> dict: ...
    def cancel_all_orders(self, symbol: str | None = None) -> dict: ...
    def get_open_orders(self, symbol: str | None = None) -> Any: ...
    def get_all_symbols(self) -> Any: ...
    def get_part_order_book(self, symbol: str, size: str) -> Any: ...
    def add_margin_order(
        self,
        symbol: str,
        side: Any,
        order_type: Any,
        size: float,
        price: float = 0,
        time_in_force: Any = ...,
    ) -> Any: ...
    def get_margin_order(self, order_id: Any) -> Any: ...
