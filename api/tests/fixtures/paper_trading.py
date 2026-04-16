from __future__ import annotations

from uuid import UUID
from typing import List
from sqlalchemy import delete
from sqlmodel import Session

from databases.tables.bot_table import PaperTradingTable

PAPER_TRADING_FIXTURE_ROWS = [
    {
        "id": "87c18ab2-5575-4330-aa14-95d3fbbe99d7",
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "fiat_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailing",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailing": False,
        "mode": "manual",
        "name": "Default bot",
        "status": "inactive",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 3.0,
        "trailing_profit": 0.0,
        "margin_short_reversal": False,
        "position": "long",
        "deal_id": "550e8400-e29b-41d4-a716-446655440001",
    },
    {
        "id": "86da4c65-2728-4625-be61-a1d5f44d706f",
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "fiat_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailing",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailing": False,
        "mode": "manual",
        "name": "Default bot",
        "status": "inactive",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 3.0,
        "trailing_profit": 0.0,
        "margin_short_reversal": False,
        "position": "long",
        "deal_id": "550e8400-e29b-41d4-a716-446655440002",
    },
    {
        "id": "2d1966f6-0924-45ab-ae47-2b8c20408e22",
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "fiat_order_size": 50,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailing",
        "cooldown": 0,
        "created_at": 1743217942076,
        "updated_at": 1743217942076,
        "dynamic_trailing": True,
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "inactive",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 2.8,
        "trailing_profit": 2.3,
        "margin_short_reversal": True,
        "position": "long",
        "deal_id": "550e8400-e29b-41d4-a716-446655440003",
    },
    {
        "id": "3c3dd13e-4233-4e91-b27b-97459ff33fe7",
        "pair": "EPICUSDC",
        "fiat": "USDC",
        "fiat_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailing",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailing": False,
        "mode": "manual",
        "name": "Test bot",
        "status": "inactive",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 3.0,
        "trailing_profit": 0.0,
        "margin_short_reversal": False,
        "position": "long",
        "deal_id": "550e8400-e29b-41d4-a716-446655440004",
    },
]


def build_paper_trading_rows() -> List[PaperTradingTable]:
    bots: List[PaperTradingTable] = []
    for row in PAPER_TRADING_FIXTURE_ROWS:
        id = UUID(str(row["id"]))
        deal_id = UUID(str(row["deal_id"]))
        bots.append(
            PaperTradingTable(
                id=id,
                pair=row["pair"],
                fiat=row["fiat"],
                fiat_order_size=row["fiat_order_size"],
                candlestick_interval=row["candlestick_interval"],
                close_condition=row["close_condition"],
                cooldown=row["cooldown"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                dynamic_trailing=row["dynamic_trailing"],
                mode=row["mode"],
                name=row["name"],
                status=row["status"],
                stop_loss=row["stop_loss"],
                take_profit=row["take_profit"],
                trailing=row["trailing"],
                trailing_deviation=row["trailing_deviation"],
                trailing_profit=row["trailing_profit"],
                margin_short_reversal=row["margin_short_reversal"],
                position=row["position"],
                deal_id=deal_id,
            )
        )
    return bots


def seed_paper_trading_defaults(session: Session, commit: bool = True) -> None:
    session.exec(delete(PaperTradingTable))
    bots = build_paper_trading_rows()
    session.add_all(bots)
    if commit:
        session.commit()
