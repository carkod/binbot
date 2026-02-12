from time import time
from typing import Optional, cast
from sqlalchemy.orm import QueryableAttribute
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import select, Session
from databases.crud.symbols_crud_utils import SymbolsCrudUtils
from tools.config import Config
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.asset_index_table import AssetIndexTable, SymbolIndexLink
from databases.tables.symbol_exchange_table import SymbolExchangeTable
from databases.tables.symbol_table import SymbolTable
from databases.utils import independent_session, engine
from symbols.models import SymbolModel, SymbolRequestPayload
from pybinbot import ExchangeId, BinanceApi, BinbotErrors, KucoinApi
from sqlalchemy.sql import delete
from exchange_apis.kucoin.futures.api import KucoinFutures
from databases.utils import get_db_session


class SymbolsCrud(SymbolsCrudUtils):
    """
    Database operations for SymbolTable using short-lived sessions.
    """

    def __init__(self, session: Optional[Session] = None):
        super().__init__()
        if not session:
            self.session = independent_session()
        else:
            self.session = session

        self.config = Config()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.kucoin_futures_api = KucoinFutures()
        self.autotrade_crud = AutotradeCrud()
        self.autotrade_settings = self.autotrade_crud.get_settings()
        self.exchange_id = self.autotrade_settings.exchange_id

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
        with get_db_session() as session:
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

        with get_db_session() as s:
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
        with get_db_session() as s:
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

    def edit_symbol_item(self, data: SymbolRequestPayload) -> SymbolModel:
        with get_db_session() as s:
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

        with get_db_session() as s:
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
        with get_db_session() as s:
            statement = select(SymbolTable).where(SymbolTable.id == symbol)
            symbol_table = s.exec(statement).first()

            if not symbol_table:
                raise BinbotErrors("Symbol not found")

            s.delete(symbol_table)
            # deletion committed by get_db_session()
            return symbol_model

    def delete_all(self):
        # keep this as-is but using a fresh session
        with Session(engine) as session:
            session.execute(delete(SymbolIndexLink))
            session.commit()
            session.execute(delete(SymbolTable))
            session.commit()
