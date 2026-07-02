from time import time
from typing import Optional
from sqlmodel import select, Session
from api.databases.crud.symbols_crud_utils import SymbolsCrudUtils
from api.tools.config import Config
from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.symbol_table import SymbolTable
from api.databases.utils import engine
from api.symbols.models import SymbolRequestPayload
from pybinbot import (
    ExchangeId,
    BinanceApi,
    BinbotErrors,
    KucoinApi,
    MarketType,
    KucoinFutures,
    SymbolModel,
)
from sqlalchemy.sql import delete
from api.databases.utils import get_db_session


class SymbolsCrud(SymbolsCrudUtils):
    """
    Database operations for SymbolTable using short-lived sessions.
    """

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.kucoin_futures_api = KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
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
        futures_leverage: int = 1,
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
                futures_leverage=futures_leverage,
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
                futures_leverage=symbol_table.futures_leverage,
                quote_asset=symbol_table.quote_asset,
                base_asset=symbol_table.base_asset,
                exchange_id=exchange_link.exchange_id,
                is_margin_trading_allowed=exchange_link.is_margin_trading_allowed,
                price_precision=exchange_link.price_precision,
                qty_precision=exchange_link.qty_precision,
                min_notional=exchange_link.min_notional,
            )
        return result

    def get_all(
        self,
        active: Optional[bool] = None,
        market_type: MarketType | None = None,
    ) -> list[SymbolModel]:
        statement = self._exchange_combined_statement(
            self.exchange_id, market_type=market_type
        )

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
                    futures_leverage=result.futures_leverage,
                    id=result.id,
                    quote_asset=result.quote_asset,
                    base_asset=result.base_asset,
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
                    futures_leverage=result.futures_leverage,
                    id=result.id,
                    quote_asset=result.quote_asset,
                    base_asset=result.base_asset,
                    exchange_id=ev.exchange_id,
                    is_margin_trading_allowed=ev.is_margin_trading_allowed,
                    price_precision=ev.price_precision,
                    qty_precision=ev.qty_precision,
                    min_notional=ev.min_notional,
                )
                return data
            else:
                raise BinbotErrors("Symbol not found")

    def start_cooldown(self, symbol: str, cooldown_seconds: int) -> None:
        with get_db_session() as session:
            symbol_table = session.get(SymbolTable, symbol)
            if symbol_table is None:
                raise BinbotErrors("Symbol not found")

            now_ms = int(time() * 1000)
            symbol_table.cooldown = max(int(cooldown_seconds), 0)
            symbol_table.cooldown_start_ts = now_ms
            symbol_table.updated_at = now_ms
            session.add(symbol_table)

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
            symbol_table.futures_leverage = data.futures_leverage

            s.add(symbol_table)
            s.flush()
            s.refresh(symbol_table)

            result = SymbolModel(
                id=symbol_table.id,
                active=symbol_table.active,
                blacklist_reason=symbol_table.blacklist_reason,
                cooldown=symbol_table.cooldown,
                cooldown_start_ts=symbol_table.cooldown_start_ts,
                futures_leverage=symbol_table.futures_leverage,
                quote_asset=symbol_table.quote_asset,
                base_asset=symbol_table.base_asset,
                exchange_id=data.exchange_id,
                is_margin_trading_allowed=data.is_margin_trading_allowed,
                price_precision=data.price_precision,
                qty_precision=data.qty_precision,
                min_notional=data.min_notional,
            )
            return result

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
        with Session(engine) as session:
            session.execute(delete(SymbolTable))
            session.commit()
