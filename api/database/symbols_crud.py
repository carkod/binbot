from database.utils import independent_session
from sqlmodel import Session, select
from database.models.symbol_table import SymbolTable
from typing import Optional
from tools.exceptions import BinbotErrors
from apis import BinanceApi
from symbols.models import SymbolPayload


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

    def get_all(self, active: Optional[bool] = True):
        """
        Get all symbols
        this excludes blacklisted items.

        To get blacklisted items set active to False
        """

        statement = select(SymbolTable)
        if active is not None:
            # cooldown_start_ts is in milliseconds
            # cooldown is in seconds
            statement = statement.where(SymbolTable.active == active).where(
                SymbolTable.cooldown_start_ts < (SymbolTable.cooldown * 1000)
            )

        results = self.session.exec(statement).all()
        self.session.close()
        return results

    def get_symbol(self, symbol: str) -> SymbolTable:
        """
        Get single symbol
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

        data = SymbolPayload.model_validate(data)
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

    def refresh_symbols_table(self):
        """
        Refresh the symbols table

        Uses ticker instead of exchange_info
        because weight considerably lower
        """
        binance_api = BinanceApi()
        data = binance_api._exchange_info()["symbols"]

        for item in data:
            if item["status"] != "TRADING":
                continue
            try:
                symbol = self.get_symbol(item["symbol"])
            except BinbotErrors:
                symbol = None
                pass

            # Only store fiat market, exclude other fiats.
            if (
                item["symbol"].endswith("USDC")
                and not symbol
                and not item["symbol"].startswith(
                    ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
                )
            ):
                price_precision = binance_api.calculate_price_precision(item["symbol"])
                qty_precision = binance_api.calculate_qty_precision(item["symbol"])
                min_notional = binance_api.min_notional_by_symbol(item["symbol"])
                active = True

                if (
                    item["symbol"] == "BTCUSDC"
                    or item["symbol"] == "ETHUSDC"
                    or item["symbol"] == "BNBUSDC"
                ):
                    active = False

                self.add_symbol(
                    item["symbol"],
                    active=active,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=float(min_notional),
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                )
