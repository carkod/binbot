import logging
from contextlib import contextmanager
from decimal import Decimal
from time import time
from typing import Optional, cast

from sqlalchemy import text, exists
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import select, Session

from exchange_apis.binance.base import BinanceApi
from exchange_apis.kucoin.base import KucoinApi
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.asset_index_crud import AssetIndexCrud
from databases.tables.asset_index_table import AssetIndexTable, SymbolIndexLink
from databases.tables.symbol_exchange_table import SymbolExchangeTable
from databases.tables.symbol_table import SymbolTable
from databases.utils import independent_session, engine
from symbols.models import SymbolModel, SymbolRequestPayload
from pybinbot.enum import QuoteAssets, ExchangeId
from tools.exceptions import BinbotErrors
from sqlalchemy.sql import delete


# -------------------------
# Session helper
# -------------------------
@contextmanager
def get_session():
    """
    Yields a fresh session. Commits on success, rolls back on exception, always closes.
    Uses your existing independent_session() factory so this integrates with your config.
    """
    session = independent_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class SymbolsCrud:
    """
    Database operations for SymbolTable using short-lived sessions.
    """

    def __init__(self, session: Optional[Session] = None):
        if not session:
            self.session = independent_session()
        else:
            self.session = session

        # keep API instances as before
        self.binance_api = BinanceApi()
        self.kucoin_api = KucoinApi()
        self.autotrade_crud = AutotradeCrud()
        self.autotrade_settings = self.autotrade_crud.get_settings()
        self.exchange_id = self.autotrade_settings.exchange_id

    # -------------------------
    # Utility helpers
    # -------------------------
    def _convert_to_int(self, value: str) -> int:
        parsed_value = str(value.rstrip(".0"))
        decimal = Decimal(parsed_value).as_tuple()
        exponent = abs(int(decimal.exponent))
        return exponent

    def _exchange_combined_statement(self, exchange_id: ExchangeId):
        exchange_exists = exists().where(
            cast(ColumnElement, SymbolExchangeTable.exchange_id == exchange_id)
            & cast(ColumnElement, SymbolExchangeTable.symbol_id == SymbolTable.id)
        )

        statement = (
            select(SymbolTable)
            .options(
                selectinload(cast(QueryableAttribute, SymbolTable.exchange_values)),
                selectinload(cast(QueryableAttribute, SymbolTable.asset_indices)),
            )
            .where(exchange_exists)
        )
        return statement

    # -------------------------
    # Insert / update helpers (explicit session)
    # -------------------------
    def _add_exchange_link_if_not_exists(
        self,
        session: Session,
        symbol: str,
        exchange_id: str,
        min_notional: float,
        price_precision: int,
        qty_precision: int,
        quote_asset: str,
        base_asset: str,
        is_margin_trading_allowed: bool,
    ):
        existing_exchange_link = session.exec(
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
            session.add(exchange_link)
            # commit/refresh handled by get_session() caller
            session.flush()
            session.refresh(exchange_link)
            return exchange_link
        return existing_exchange_link

    def add_symbol(
        self,
        symbol: str,
        quote_asset: str,
        base_asset: str,
        exchange_id: ExchangeId,
        active: bool = True,
        reason: Optional[str] = "",
        price_precision: int = 0,
        qty_precision: int = 0,
        min_notional: float = 0,
        cooldown: int = 0,
        cooldown_start_ts: int = 0,
        is_margin_trading_allowed: bool = False,
    ) -> SymbolModel:
        # use a fresh session to avoid blockers from long-live transactions
        with get_session() as session:
            symbol_table = SymbolTable(
                id=symbol,
                blacklist_reason=reason or "",
                active=active,
                cooldown=cooldown,
                cooldown_start_ts=cooldown_start_ts,
                quote_asset=quote_asset,
                base_asset=base_asset,
            )
            session.add(symbol_table)
            session.flush()
            session.refresh(symbol_table)

            exchange_link = SymbolExchangeTable(
                symbol_id=symbol,
                exchange_id=exchange_id,
                min_notional=min_notional,
                price_precision=price_precision,
                qty_precision=qty_precision,
                is_margin_trading_allowed=is_margin_trading_allowed,
            )
            session.add(exchange_link)
            session.flush()
            session.refresh(exchange_link)

            result = SymbolModel(
                id=symbol_table.id,
                active=symbol_table.active,
                blacklist_reason=symbol_table.blacklist_reason,
                cooldown=symbol_table.cooldown,
                cooldown_start_ts=symbol_table.cooldown_start_ts,
                quote_asset=symbol_table.quote_asset,
                base_asset=symbol_table.base_asset,
                exchange_id=exchange_link.exchange_id,
                is_margin_trading_allowed=exchange_link.is_margin_trading_allowed,
                price_precision=exchange_link.price_precision,
                qty_precision=exchange_link.qty_precision,
                min_notional=exchange_link.min_notional,
                asset_indices=[],
            )
        return result

    # -------------------------
    # Precision helper
    # -------------------------
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

    # -------------------------
    # Read helpers (session-per-op)
    # -------------------------
    def get_all(
        self, active: Optional[bool] = None, index_id: Optional[str] = None
    ) -> list[SymbolModel]:
        statement = self._exchange_combined_statement(self.exchange_id)

        if index_id is not None:
            statement = statement.join(
                cast(QueryableAttribute, SymbolTable.asset_indices)
            ).where(AssetIndexTable.id == index_id)

        if active is not None:
            statement = statement.where(SymbolTable.active == active)
            statement = statement.where(
                SymbolTable.cooldown_start_ts + (SymbolTable.cooldown * 1000)
                < (time() * 1000)
            )

        with get_session() as s:
            results = s.exec(statement).unique().all()

            list_results: list[SymbolModel] = []
            for result in results:
                exchange_values = result.exchange_values or []
                if not exchange_values:
                    continue
                ev = exchange_values[0]
                data = SymbolModel(
                    active=result.active,
                    blacklist_reason=result.blacklist_reason,
                    cooldown=result.cooldown,
                    cooldown_start_ts=result.cooldown_start_ts,
                    id=result.id,
                    quote_asset=result.quote_asset,
                    base_asset=result.base_asset,
                    asset_indices=[
                        AssetIndexTable(id=index.id, name=index.name)
                        for index in result.asset_indices
                    ],
                    exchange_id=ev.exchange_id,
                    is_margin_trading_allowed=ev.is_margin_trading_allowed,
                    price_precision=ev.price_precision,
                    qty_precision=ev.qty_precision,
                    min_notional=ev.min_notional,
                )
                list_results.append(data)
            return list_results

    def get_symbol(self, symbol: str) -> SymbolModel:
        statement = self._exchange_combined_statement(self.exchange_id).where(
            SymbolTable.id == symbol
        )
        with get_session() as s:
            result = s.exec(statement).first()
            if result:
                exchange_values = result.exchange_values or []
                if not exchange_values:
                    raise BinbotErrors(
                        "No exchange values found for symbol and exchange"
                    )
                for exchange_value in exchange_values:
                    if exchange_value.exchange_id == self.exchange_id:
                        ev = exchange_value
                        break
                else:
                    ev = exchange_values[0]

                data = SymbolModel(
                    active=result.active,
                    blacklist_reason=result.blacklist_reason,
                    cooldown=result.cooldown,
                    cooldown_start_ts=result.cooldown_start_ts,
                    id=result.id,
                    quote_asset=result.quote_asset,
                    base_asset=result.base_asset,
                    asset_indices=[
                        AssetIndexTable(id=index.id, name=index.name)
                        for index in result.asset_indices
                    ],
                    exchange_id=ev.exchange_id,
                    is_margin_trading_allowed=ev.is_margin_trading_allowed,
                    price_precision=ev.price_precision,
                    qty_precision=ev.qty_precision,
                    min_notional=ev.min_notional,
                )
                return data
            else:
                raise BinbotErrors("Symbol not found")

    # -------------------------
    # Update / edit
    # -------------------------
    def edit_symbol_item(self, data: SymbolRequestPayload) -> SymbolModel:
        with get_session() as s:
            statement = select(SymbolTable).where(SymbolTable.id == data.symbol)
            symbol_table = s.exec(statement).first()

            if not symbol_table:
                raise BinbotErrors("Symbol not found")

            symbol_table.active = data.active
            if data.blacklist_reason:
                symbol_table.blacklist_reason = data.blacklist_reason
            if data.cooldown:
                symbol_table.cooldown = data.cooldown
            if data.cooldown_start_ts:
                symbol_table.cooldown_start_ts = data.cooldown_start_ts

            s.add(symbol_table)
            s.flush()
            s.refresh(symbol_table)

            result = SymbolModel(
                id=symbol_table.id,
                active=symbol_table.active,
                blacklist_reason=symbol_table.blacklist_reason,
                cooldown=symbol_table.cooldown,
                cooldown_start_ts=symbol_table.cooldown_start_ts,
                quote_asset=symbol_table.quote_asset,
                base_asset=symbol_table.base_asset,
                exchange_id=data.exchange_id,
                is_margin_trading_allowed=data.is_margin_trading_allowed,
                price_precision=data.price_precision,
                qty_precision=data.qty_precision,
                min_notional=data.min_notional,
                asset_indices=[
                    AssetIndexTable(id=index.id, name=index.name)
                    for index in symbol_table.asset_indices
                ],
            )
            return result

    def update_symbol_indexes(self, data: SymbolRequestPayload):
        data_id = getattr(data, "id", None) or getattr(data, "symbol", None)
        symbol_model = self.get_symbol(cast(str, data_id))

        with get_session() as s:
            stmt = delete(SymbolIndexLink).where(
                cast(ColumnElement, SymbolIndexLink.symbol_id == symbol_model.id)
            )
            s.execute(stmt)

            for index_id in data.asset_indices:
                asset_index = s.exec(
                    select(AssetIndexTable).where(AssetIndexTable.id == index_id.id)
                ).first()
                if not asset_index:
                    asset_index = AssetIndexTable(id=index_id.id, name=index_id.name)
                    s.add(asset_index)
                    s.flush()
                link = SymbolIndexLink(
                    symbol_id=symbol_model.id, asset_index_id=asset_index.id
                )
                s.add(link)

            s.flush()
            s.refresh(symbol_model)
            return symbol_model

    def delete_symbol(self, symbol: str):
        symbol_model = self.get_symbol(symbol)
        with get_session() as s:
            statement = select(SymbolTable).where(SymbolTable.id == symbol)
            symbol_table = s.exec(statement).first()

            if not symbol_table:
                raise BinbotErrors("Symbol not found")

            s.delete(symbol_table)
            # deletion committed by get_session()
            return symbol_model

    def delete_all(self):
        # keep this as-is but using a fresh session
        with Session(engine) as session:
            session.execute(delete(SymbolIndexLink))
            session.commit()
            session.execute(delete(SymbolTable))
            session.commit()

    def base_asset(self, symbol: str) -> Optional[str]:
        query = select(SymbolTable.base_asset).where(SymbolTable.id == symbol)
        with get_session() as s:
            base_asset = s.exec(query).first()
            return base_asset

    # -------------------------
    # Exchange ingestion / ETL
    # -------------------------
    def binance_symbols_reingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        for item in exchange_info_data["symbols"]:
            if item["status"] != "TRADING":
                continue
            if item["quoteAsset"] == "TRY":
                continue

            try:
                self.get_symbol(item["symbol"])
            except BinbotErrors:
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def kucoin_symbols_reingestion(self):
        exchange_info_data = self.kucoin_api.get_all_symbols()
        for item in exchange_info_data.data:
            symbol = item.symbol.replace("-", "")
            if not item.enable_trading or item.symbol.startswith(
                ("DOWN", "UP", "AUD", "EUR", "GBP")
            ):
                continue

            if item.st:
                # assets to be delisted
                payload = SymbolRequestPayload(
                    symbol=symbol,
                    active=False,
                    blacklist_reason="At risk to be delisted soon",
                    exchange_id=ExchangeId.KUCOIN,
                    min_notional=float(item.base_min_size),
                    price_precision=item.price_increment.find("1") - 2,
                    qty_precision=item.base_increment.find("1") - 2,
                    is_margin_trading_allowed=item.is_margin_enabled,
                    quote_asset=item.quote_currency,
                    base_asset=item.base_currency,
                )
                try:
                    self.edit_symbol_item(payload)
                    continue

                except Exception as e:
                    self.session.rollback()
                    logging.error(f"Error updating delisted symbol {symbol}: {e}")
                    continue

            active = True
            if symbol in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                active = False

            if item.quote_currency in list(QuoteAssets):
                price_precision = item.price_increment.find("1") - 2
                qty_precision = item.base_increment.find("1") - 2
                min_notional = float(item.base_min_size)

                statement = select(SymbolTable).where(SymbolTable.id == symbol)
                result = self.session.exec(statement).first()
                if result:
                    with get_session() as s:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )
                else:
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
                    with get_session() as s:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )

    def binance_symbols_ingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        for item in exchange_info_data["symbols"]:
            if item["status"] != "TRADING" or item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue
            if item["quoteAsset"] == "TRY":
                continue
            if item["quoteAsset"] in list(QuoteAssets):
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def kucoin_symbols_ingestion(self):
        exchange_info_data = self.kucoin_api.get_all_symbols()
        for item in exchange_info_data.data:
            symbol = item.symbol.replace("-", "")
            if not item.enable_trading or item.symbol.startswith(
                ("DOWN", "UP", "AUD", "EUR", "GBP")
            ):
                continue

            active = True
            if symbol in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                active = False

            if item.quote_currency in list(QuoteAssets):
                price_precision = item.price_increment.find("1") - 2
                qty_precision = item.base_increment.find("1") - 2
                min_notional = float(item.base_min_size)

                with get_session() as s:
                    result = s.exec(
                        select(SymbolTable).where(SymbolTable.id == symbol)
                    ).first()
                    if result:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )
                    else:
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
                        # ensure exchange link added in same session
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )

    def etl_symbols_ingestion(self, delete_existing: bool = False):
        if delete_existing:
            # TRUNCATE in its own fresh session so it never conflicts with earlier SELECTs
            with get_session() as s:
                s.execute(text("TRUNCATE TABLE symbol CASCADE"))

            asset_index_crud = AssetIndexCrud()
            asset_index_crud.delete_all()

        # Run ingestions
        self.binance_symbols_ingestion()
        self.kucoin_symbols_ingestion()

    def etl_symbols_updates(self):
        self.kucoin_symbols_reingestion()
