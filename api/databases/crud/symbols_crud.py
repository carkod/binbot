from exchange_apis.kucoin import KucoinApi
from databases.crud.asset_index_crud import AssetIndexCrud
from databases.tables.asset_index_table import AssetIndexTable, SymbolIndexLink
from databases.utils import independent_session
from sqlmodel import Session, select, SQLModel
from databases.tables.symbol_table import SymbolTable
from databases.tables.symbol_exchange_table import SymbolExchangeTable
from typing import Optional
from tools.exceptions import BinbotErrors
from exchange_apis.binance import BinanceApi
from symbols.models import SymbolModel, SymbolRequestPayload, ExchangeValueModel
from decimal import Decimal
from time import time
from typing import cast
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlalchemy.sql import delete
from databases.utils import engine
from tools.enum_definitions import QuoteAssets, ExchangeId
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy import text


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

    def _exchange_combined_statement(self):
        """
        Multi-exchange support

        Query becomes quite complex and we always need to do this
        only to be used in this CRUD class
        """
        statement = (
            select(SymbolTable)
            .options(
                selectinload(cast(QueryableAttribute, SymbolTable.exchange_values)),
                selectinload(cast(QueryableAttribute, SymbolTable.asset_indices)),
            )
            .join(SymbolExchangeTable, SymbolExchangeTable.symbol_id == SymbolTable.id)
        )
        return statement

    def _add_exchange_link_if_not_exists(
        self,
        symbol: str,
        exchange_id: str,
        min_notional: float,
        price_precision: int,
        qty_precision: int,
        quote_asset: str,
        base_asset: str,
        is_margin_trading_allowed: bool,
    ):
        """
        Add SymbolExchangeTable entry if it does not already exist for the given symbol and exchange.
        """
        existing_exchange_link = self.session.exec(
            select(SymbolExchangeTable).where(
                (SymbolExchangeTable.symbol_id == symbol)
                & (SymbolExchangeTable.exchange_id == exchange_id)
            )
        ).first()
        if not existing_exchange_link:
            exchange_link = SymbolExchangeTable(
                symbol_id=symbol,
                exchange_id=exchange_id,
                min_notional=min_notional,
                price_precision=price_precision,
                qty_precision=qty_precision,
                quote_asset=quote_asset,
                base_asset=base_asset,
                is_margin_trading_allowed=is_margin_trading_allowed,
            )
            self.session.add(exchange_link)
            self.session.commit()
            self.session.refresh(exchange_link)
            return exchange_link
        return existing_exchange_link

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
        self,
        active: Optional[bool] = None,
        index_id: Optional[str] = None,
    ) -> list[SymbolModel]:
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

        statement = self._exchange_combined_statement()

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
        # Normalise data
        list_results = []
        for result in results:
            data = SymbolModel(
                active=result.active,
                blacklist_reason=result.blacklist_reason,
                cooldown=result.cooldown,
                cooldown_start_ts=result.cooldown_start_ts,
                id=result.id,
                exchange_id=result.exchange_values[0].exchange_id,
                quote_asset=result.quote_asset,
                base_asset=result.base_asset,
                asset_indices=[
                    AssetIndexTable(id=index.id, name=index.name)
                    for index in result.asset_indices
                ],
                exchange_values={
                    ev.exchange_id: ExchangeValueModel(
                        is_margin_trading_allowed=ev.is_margin_trading_allowed,
                        price_precision=ev.price_precision,
                        qty_precision=ev.qty_precision,
                        min_notional=ev.min_notional,
                    )
                    for ev in result.exchange_values
                },
            )
            list_results.append(data)
        self.session.close()
        return list_results

    def get_symbol(self, symbol: str) -> SymbolModel:
        """
        Get single symbol

        Returns a single symbol dict
        """
        statement = self._exchange_combined_statement().where(SymbolTable.id == symbol)

        result = self.session.exec(statement).first()
        if result:
            # normalise data
            data = SymbolModel(
                active=result.active,
                blacklist_reason=result.blacklist_reason,
                cooldown=result.cooldown,
                cooldown_start_ts=result.cooldown_start_ts,
                id=result.id,
                exchange_id=result.exchange_values[0].exchange_id,
                quote_asset=result.quote_asset,
                base_asset=result.base_asset,
                asset_indices=[
                    AssetIndexTable(id=index.id, name=index.name)
                    for index in result.asset_indices
                ],
                min_notional=result.exchange_values[0].min_notional,
                price_precision=result.exchange_values[0].price_precision,
                qty_precision=result.exchange_values[0].qty_precision,
                is_margin_trading_allowed=result.exchange_values[
                    0
                ].is_margin_trading_allowed,
            )

            self.session.close()
            return data
        else:
            self.session.close()
            raise BinbotErrors("Symbol not found")

    def add_symbol(
        self,
        symbol: str,
        quote_asset: str,
        base_asset: str,
        exchange_id: str,
        active: bool = True,
        reason: Optional[str] = "",
        price_precision: int = 0,
        qty_precision: int = 0,
        min_notional: float = 0,
        cooldown: int = 0,
        cooldown_start_ts: int = 0,
        is_margin_trading_allowed: bool = False,
    ) -> SymbolExchangeTable:
        """
        Add a new symbol and its exchange-specific data
        """
        symbol_table = SymbolTable(
            id=symbol,
            blacklist_reason=reason,
            active=active,
            cooldown=cooldown,
            cooldown_start_ts=cooldown_start_ts,
            quote_asset=quote_asset,
            base_asset=base_asset,
        )
        self.session.add(symbol_table)
        self.session.commit()
        self.session.refresh(symbol_table)
        # Add exchange-specific data
        exchange_link = SymbolExchangeTable(
            symbol_id=symbol,
            exchange_id=exchange_id,
            min_notional=min_notional,
            price_precision=price_precision,
            qty_precision=qty_precision,
            is_margin_trading_allowed=is_margin_trading_allowed,
        )
        self.session.add(exchange_link)
        self.session.commit()
        self.session.refresh(exchange_link)
        self.session.close()
        return exchange_link

    def edit_symbol_item(
        self,
        data: SymbolRequestPayload,
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

    def update_symbol_indexes(self, data: SymbolRequestPayload):
        """
        Update the asset indices (tags) for a symbol.
        Only updates the link table, so multiple symbols can share the same asset index.
        """
        symbol_model = self.get_symbol(data.id)

        # Remove all existing links for this symbol
        stmt = delete(SymbolIndexLink).where(
            cast(ColumnElement, SymbolIndexLink.symbol_id == symbol_model.id)
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

    def base_asset(self, symbol: str) -> Optional[str]:
        """
        Finds base asset using Symbols database
        e.g. BTCUSDC -> BTC
        """
        query = select(SymbolTable.base_asset).where(SymbolTable.id == symbol)
        base_asset = self.session.exec(query).first()
        return base_asset

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
                    price_precision=price_filter["tickSize"] if price_filter else 0,
                    qty_precision=quantity_filter["stepSize"] if quantity_filter else 0,
                    min_notional=(
                        min_notional_filter["minNotional"] if min_notional_filter else 0
                    ),
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    is_margin_trading_allowed=item["isMarginTradingAllowed"],
                    asset_indices=[],
                )
                self.session.add(symbol)
        self.session.commit()

    def binance_symbols_ingestion(self):
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
        for item in exchange_info_data["symbols"]:
            symbol = None
            # Only store fiat market exclude other fiats.
            # Only store pairs that are actually traded
            if item["status"] != "TRADING" or item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue

            if item["quoteAsset"] in list(QuoteAssets) and symbol is None:
                active = True
                if item["symbol"] in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                    active = False

                # Calculate exchange-specific fields
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=active,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item["isMarginTradingAllowed"],
                )

        self.session.close()

    def kucoin_symbols_ingestion(self):
        """
        Full data ingestions of symbol (e.g. BTC-USDT)
        for the symbols table from Kucoin exchange
        """
        kucoin_api = KucoinApi()
        exchange_info_data = kucoin_api.get_all_symbols()

        for item in exchange_info_data.data:
            # Only store fiat market exclude other fiats.
            # Only store pairs that are actually traded
            if item.enable_trading is not True or item.symbol.startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue

            active = True
            if item.symbol in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                active = False

            if item.quote_currency in list(QuoteAssets):
                symbol = item.symbol.replace("-", "")
                price_precision = item.price_increment.find("1") - 2
                qty_precision = item.base_increment.find("1") - 2
                min_notional = float(item.base_min_size)

                try:
                    self.get_symbol(symbol=symbol)
                    self._add_exchange_link_if_not_exists(
                        symbol=symbol,
                        exchange_id=ExchangeId.KUCOIN,
                        min_notional=min_notional,
                        price_precision=price_precision,
                        qty_precision=qty_precision,
                        quote_asset=item.quote_currency,
                        base_asset=item.base_currency,
                        is_margin_trading_allowed=item.is_margin_enabled,
                    )

                except BinbotErrors as error:
                    if "Symbol not found" in str(error):
                        self.add_symbol(
                            symbol=symbol,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            exchange_id=ExchangeId.KUCOIN,
                            active=active,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            min_notional=min_notional,
                        )

                        self._add_exchange_link_if_not_exists(
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )

                except Exception as error:
                    print(f"Error adding symbol {symbol}: {error}")
                    # Create SymbolTable entry

                    pass

        self.session.close()

    def etl_symbols_ingestion(self, delete_existing: bool = False):
        """
        ETL process to ingest symbols from multiple exchanges
        Populates both SymbolTable and SymbolExchangeTable
        """
        if delete_existing:
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS symbol CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS symbol_exchange CASCADE"))
                conn.commit()
                SQLModel.metadata.create_all(engine)
                # Delete index tables, these will be refilled later
                asset_index_crud = AssetIndexCrud()
                asset_index_crud.delete_all()

        self.binance_symbols_ingestion()
        self.kucoin_symbols_ingestion()
