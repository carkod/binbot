from decimal import Decimal
from typing import Optional, Union, cast
from sqlalchemy import exists
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import select, Session
from databases.tables.symbol_exchange_table import SymbolExchangeTable
from databases.tables.symbol_table import SymbolTable
from databases.utils import get_db_session
from pybinbot import ExchangeId


class SymbolsCrudUtils:
    # -------------------------
    # Utility helpers
    # -------------------------
    def _convert_to_int(self, value: Union[float, str]) -> int:
        dec = Decimal(str(value))
        exponent = int(dec.as_tuple().exponent)
        return abs(exponent)

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
            # commit/refresh handled by get_db_session() caller
            session.flush()
            session.refresh(exchange_link)
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

    def base_asset(self, symbol: str) -> Optional[str]:
        query = select(SymbolTable.base_asset).where(SymbolTable.id == symbol)
        with get_db_session() as s:
            base_asset = s.exec(query).first()
            return base_asset
