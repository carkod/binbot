from databases.crud.asset_index_crud import AssetIndexCrud
from databases.models.asset_index_table import AssetIndexTable, SymbolIndexLink
from databases.utils import independent_session
from sqlmodel import Session, select
from databases.models.symbol_table import SymbolTable
from typing import Optional
from tools.exceptions import BinbotErrors
from exchange_apis.binance import BinanceApi
from symbols.models import SymbolPayload
from decimal import Decimal
from time import time
from typing import cast
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlalchemy.sql import delete
from databases.utils import engine
from tools.enum_definitions import QuoteAssets
from tools.maths import round_numbers


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
        self.binance_api = BinanceApi()

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

    def get_all(
        self, active: Optional[bool] = None, index_id: Optional[str] = None
    ) -> list[SymbolTable]:
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

        statement = select(SymbolTable).options(
            selectinload(cast(QueryableAttribute, SymbolTable.asset_indices))
        )

        if index_id is not None:
            # cast here is used to avoid mypy complaining
            statement = statement.join(
                cast(QueryableAttribute, SymbolTable.asset_indices)
            ).where(AssetIndexTable.id == index_id)

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
        return list(results)

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
            self.session.close()
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
        Edit a symbol item (previously known as blacklisted)

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

    def update_symbol_indexes(self, data: SymbolPayload):
        """
        Update the asset indices (tags) for a symbol.
        Only updates the link table, so multiple symbols can share the same asset index.
        """
        symbol_model = self.get_symbol(data.id)

        # Remove all existing links for this symbol
        stmt = delete(SymbolIndexLink).where(
            SymbolIndexLink.symbol_id == symbol_model.id  # type: ignore[arg-type]
        )
        self.session.execute(stmt)
        self.session.commit()

        # Add new links
        for index_id in data.asset_indices:
            asset_index = self.session.exec(
                select(AssetIndexTable).where(AssetIndexTable.id == index_id.id)
            ).first()
            if not asset_index:
                asset_index = AssetIndexTable(id=index_id.id, name=index_id.name)
                self.session.add(asset_index)
                self.session.commit()
            # Create the link
            link = SymbolIndexLink(
                symbol_id=symbol_model.id, asset_index_id=asset_index.id
            )
            self.session.add(link)

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

    def delete_all(self):
        """
        Only used for cleanup and initialisation
        do not use for normal operations

        Many systems rely on this list of symbols
        """
        with Session(engine) as session:
            session.execute(delete(SymbolIndexLink))
            session.commit()
            session.execute(delete(SymbolTable))
            session.commit()

    def base_asset(self, symbol: str):
        """
        Finds base asset using Symbols database
        e.g. BTCUSDC -> BTC
        """
        query = select(SymbolTable.base_asset).where(SymbolTable.id == symbol)
        base_asset = self.session.exec(query).first()
        return base_asset

    def etl_symbols_and_indexes(self, delete_existing: bool = True):
        """
        Full data ingestions of symbol (e.g. ETHUSDC)
        for the symbols table

        This populates the table with Binance pairs from exchange_info
        future: if additional exchanges are added,
        symbol pairs should be consolidated in this table

        Indexes are populated by the binbot-notebooks
        """
        binance_api = BinanceApi()
        exchange_info_data = binance_api.exchange_info()
        symbol = None

        if delete_existing:
            # Reset symbols table (this should reset link tables)
            self.delete_all()
            # Delete index tables, these will be refilled later
            asset_index_crud = AssetIndexCrud()
            asset_index_crud.delete_all()

        for item in exchange_info_data["symbols"]:
            # Only store fiat market exclude other fiats.
            # Only store pairs that are actually traded
            if item["status"] != "TRADING" or item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue

            try:
                # Always prefer USDC quote pairs to avoid conversion
                if item["quoteAsset"] == QuoteAssets.USDC:
                    # throws error if it doesn't exist
                    symbol = self.get_symbol(item["symbol"])
                    continue

                if item["quoteAsset"] == QuoteAssets.BTC:
                    symbol = self.get_symbol(f"{item['baseAsset']}USDC")
                    continue

                if item["quoteAsset"] == QuoteAssets.ETH:
                    symbol = self.get_symbol(f"{item['baseAsset']}USDC")
                    symbol = self.get_symbol(f"{item['baseAsset']}BTC")
                    continue

            except BinbotErrors:
                symbol = None
                if item["quoteAsset"] in list(QuoteAssets) and symbol is None:
                    price_precision, qty_precision, min_notional = (
                        self.calculate_precisions(item)
                    )
                    active = True
                    if item["symbol"] in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
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
                    pass

        self.session.close()

    def etl_exchange_info_update(self):
        """
        Update the symbols table with the latest exchange information
        """
        binance_api = BinanceApi()
        exchange_info_data = binance_api.exchange_info()

        for item in exchange_info_data["symbols"]:
            if item["status"] != "TRADING":
                continue

            try:
                self.get_symbol(item["symbol"])
            except BinbotErrors:
                price_filter = next(
                    (m for m in item["filters"] if m["filterType"] == "PRICE_FILTER"),
                    None,
                )
                quantity_filter = next(
                    (m for m in item["filters"] if m["filterType"] == "LOT_SIZE"), None
                )
                min_notional_filter = next(
                    (m for m in item["filters"] if m["filterType"] == "NOTIONAL"), None
                )
                symbol = SymbolTable(
                    id=item["symbol"],
                    active=True,
                    price_precision=round_numbers(price_filter["tickSize"])
                    if price_filter
                    else 0,
                    qty_precision=round_numbers(quantity_filter["stepSize"])
                    if quantity_filter
                    else 0,
                    min_notional=round_numbers(min_notional_filter["minNotional"])
                    if min_notional_filter
                    else 0,
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    is_margin_trading_allowed=item["isMarginTradingAllowed"],
                    asset_indices=[],
                )
                self.session.add(symbol)
        self.session.commit()
