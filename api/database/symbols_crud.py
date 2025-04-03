from database.utils import independent_session
from sqlmodel import Session, select
from database.models.symbol_table import SymbolTable
from typing import Optional
from tools.exceptions import BinbotErrors
from exchange_apis.binance import BinanceApi
from symbols.models import SymbolPayload
from decimal import Decimal
from time import time
from typing import Sequence


class SymbolsCrud:
    """
    Database operations for SymbolTable
    """

    def __init__(
        self,
        # Some instances of AutotradeSettingsController are used outside of the FastAPI context
        # this is designed this way for reusability
        session: Session | None = None,
    ):
        if session is None:
            session = independent_session()
        self.session = session

    """
    Convert binance tick/step sizes to decimal
    object for calculations
    """

    def _convert_to_int(self, value: str) -> int:
        # cast to str to avoid conversion to long decimal
        # e.g. 56.4325 -> 56.4324999... by Decimal
        parsed_value = str(value.rstrip(".0"))
        decimal = Decimal(parsed_value).as_tuple()
        exponent = abs(int(decimal.exponent))
        return exponent

    def calculate_precisions(self, item) -> tuple[int, int, float]:
        price_precision = 0
        qty_precision = 0
        min_notional: float = 0

        for filter in item["filters"]:
            if filter["filterType"] == "PRICE_FILTER":
                price_precision = self._convert_to_int(filter["tickSize"])

            if filter["filterType"] == "LOT_SIZE":
                qty_precision = self._convert_to_int(filter["stepSize"])

            if filter["filterType"] == "NOTIONAL":
                min_notional = float(filter["minNotional"])

        return price_precision, qty_precision, min_notional

    def get_all(self, active: Optional[bool] = None) -> Sequence[SymbolTable]:
        """
        Get all symbols

        "Active" takes into account that we want
        symbols still ingesting candlestick data
        as well as blacklist active symbols also exclude cooldown,
        which are symbols that are used too much in Binquant
        and we want to temporarily block them

        For a single symbol, use get_symbol
        this decouples the logic for easy
        debugging/fixes and consistent response

        Args:
        - active: if True, only active symbols are returned (to trade & candlestick data & cooldown)
        - active: None, all symbols are returned

        Returns:
        - List: always returns a list,
        if no results are found, returns empty list
        """

        statement = select(SymbolTable)

        if active is not None:
            statement = statement.where(SymbolTable.active == active)
            # cooldown_start_ts is in milliseconds
            # cooldown is in seconds
            statement = statement.where(
                SymbolTable.cooldown_start_ts + (SymbolTable.cooldown * 1000)
                < (time() * 1000)
            )

        results = self.session.exec(statement).unique().all()
        self.session.close()
        return results

    def get_symbol(self, symbol: str) -> SymbolTable:
        """
        Get single symbol

        Returns a single symbol dict
        """
        statement = select(SymbolTable).where(SymbolTable.id == symbol)
        result = self.session.exec(statement).first()
        if result:
            self.session.close()
            return result
        else:
            raise BinbotErrors("Symbol not found")

    def add_symbol(
        self,
        symbol: str,
        quote_asset: str,
        base_asset: str,
        active: bool = True,
        reason: Optional[str] = "",
        price_precision: int = 0,
        qty_precision: int = 0,
        min_notional: float = 0,
        cooldown: int = 0,
        cooldown_start_ts: int = 0,
        is_margin_trading_allowed: bool = False,
    ):
        """
        Add a new symbol
        """
        symbol = SymbolTable(
            id=symbol,
            blacklist_reason=reason,
            active=active,
            price_precision=price_precision,
            qty_precision=qty_precision,
            min_notional=min_notional,
            quote_asset=quote_asset,
            base_asset=base_asset,
            cooldown=cooldown,
            cooldown_start_ts=cooldown_start_ts,
            is_margin_trading_allowed=is_margin_trading_allowed,
        )
        self.session.add(symbol)
        self.session.commit()
        self.session.refresh(symbol)
        self.session.close()
        return symbol

    def edit_symbol_item(
        self,
        data: SymbolPayload,
    ):
        """
        Edit a blacklisted item.

        Editable fields are different from SymbolTable
        fields like qty_precision, price_precision, etc.
        should be given by the exchange not modified
        by clients/users, it can lead to inconsistencies across
        the entire API.
        """

        symbol_model = self.get_symbol(data.id)
        symbol_model.active = data.active

        if data.blacklist_reason:
            symbol_model.blacklist_reason = data.blacklist_reason

        if data.cooldown:
            symbol_model.cooldown = data.cooldown

        if data.cooldown_start_ts:
            symbol_model.cooldown_start_ts = data.cooldown_start_ts

        self.session.add(symbol_model)
        self.session.commit()
        self.session.refresh(symbol_model)
        self.session.close()
        return symbol_model

    def delete_symbol(self, symbol: str):
        """
        Delete a blacklisted item
        """
        symbol_model = self.get_symbol(symbol)
        self.session.delete(symbol_model)
        self.session.commit()
        self.session.close()
        return symbol_model

    def base_asset(self, symbol: str):
        """
        Finds base asset using Symbols database
        e.g. BTCUSDC -> BTC
        """
        query = select(SymbolTable.base_asset).where(SymbolTable.id == symbol)
        base_asset = self.session.exec(query).first()
        return base_asset

    def symbols_table_ingestion(self):
        """
        Full data ingestions of symbol (e.g. ETHUSDC)
        for the symbols table

        This populates the table with Binance pairs
        future: if additional exchanges are added,
        symbol pairs should be consolidated in this table
        """
        binance_api = BinanceApi()
        exchange_info_data = binance_api.exchange_info()

        for item in exchange_info_data["symbols"]:
            # Only store fiat market exclude other fiats.
            # Only store pairs that are actually traded
            if item["status"] != "TRADING" and item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue
            try:
                symbol = self.get_symbol(item["symbol"])
            except BinbotErrors:
                symbol = None
                pass

            if item["symbol"].endswith("USDC") and symbol is None:
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                active = True

                if (
                    item["symbol"] == "BTCUSDC"
                    or item["symbol"] == "ETHUSDC"
                    or item["symbol"] == "BNBUSDC"
                ):
                    active = False

                symbol = SymbolTable(
                    id=item["symbol"],
                    active=active,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    is_margin_trading_allowed=item["isMarginTradingAllowed"],
                )
                self.session.add(symbol)
                self.session.commit()

        self.session.close()
