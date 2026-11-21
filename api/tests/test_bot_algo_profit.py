from uuid import uuid4

import pytest
from pybinbot import Position, Status
from sqlmodel import Session

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable


def test_algorithm_profit_counts_long_and_short_returns_and_open_bots(test_engine):
    name = f"profit-{uuid4()}"
    with Session(test_engine) as session:
        bots = [
            BotTable(
                pair="BTCUSDT",
                name=name,
                position=position,
                status=Status.completed if closing else Status.active,
                deal=DealTable(opening_price=opening, closing_price=closing),
            )
            for position, opening, closing in [
                (Position.long, 100, 110),
                (Position.short, 100, 80),
                (Position.short, 100, 110),
                (Position.long, 100, 0),
                (Position.short, 100, 0),
                (Position.long, 0, 110),
            ]
        ]
        session.add_all(bots)
        session.flush()

        ranking = next(
            item for item in BotTableCrud(session).get_list_algo() if item.name == name
        )

        assert ranking.count == 6
        assert ranking.bot_profit == pytest.approx(0.2)
