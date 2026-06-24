import re
from typing import Any, List, Sequence, cast
from uuid import UUID

from pybinbot import (
    AlgoRankingItem,
    BinbotErrors,
    BotBase,
    BotModel,
    OrderModel,
    Position,
    RecoveryParams,
    SaveBotError,
    Status,
    timestamp,
    ts_to_humandate,
)
from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, asc, case, col, desc, func, select

from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from databases.tables.recovery_bot_table import RecoveryBotTable
from databases.utils import detach_bot_graph, get_db_session

# Deal with SQLModel vs mypy issues
BOT_DEAL_REL = cast(QueryableAttribute[Any], BotTable.deal)
BOT_ORDERS_REL = cast(QueryableAttribute[Any], BotTable.orders)
BOT_RECOVERY_REL = cast(QueryableAttribute[Any], BotTable.recovery_params)
ACTIVE_BOT_STATUSES = (Status.active, Status.pending)


class BotTableCrud:
    """
    CRUD for BotTable.

    - If session is injected → it will be reused.
    - If not → a fresh session is created per operation.
    - Always returns ORM objects.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    @staticmethod
    def _order_field_names() -> list[str]:
        return [
            field_name
            for field_name in ExchangeOrderTable.model_fields.keys()
            if field_name not in {"id", "bot", "bot_id"}
        ]

    def _sync_order_fields(
        self, target: ExchangeOrderTable, source: OrderModel | ExchangeOrderTable
    ) -> None:
        for field_name in self._order_field_names():
            if hasattr(source, field_name):
                setattr(target, field_name, getattr(source, field_name))

    def _build_order_row(
        self, order: OrderModel | ExchangeOrderTable, bot_id: UUID | None = None
    ) -> ExchangeOrderTable:
        return ExchangeOrderTable(
            order_type=order.order_type,
            time_in_force=order.time_in_force,
            order_id=str(order.order_id),
            order_side=order.order_side,
            pair=order.pair,
            qty=order.qty,
            status=order.status,
            price=order.price,
            deal_type=order.deal_type,
            timestamp=order.timestamp,
            bot_id=bot_id,
        )

    def update_table(self, bot: BotModel | BotTable) -> BotTable:
        """
        Convert a BotModel to BotTable (or return BotTable as-is),
        fully populating deal and orders in a detached manner.
        Safe to attach to a session later for save/commit.
        """
        if isinstance(bot, BotTable):
            return bot

        # Step 1: Copy BotModel fields (except relationships)
        bot_table = BotTable()
        for field_name in BotTable.model_fields.keys():
            if field_name in {
                "deal",
                "orders",
                "recovery_mode_id",
                "recovery_params",
            }:
                continue
            if hasattr(bot, field_name):
                setattr(bot_table, field_name, getattr(bot, field_name))

        # Step 2: Copy DealTable fields
        bot_table.deal = DealTable()
        if bot.deal:
            for field_name in DealTable.model_fields.keys():
                if hasattr(bot.deal, field_name):
                    setattr(bot_table.deal, field_name, getattr(bot.deal, field_name))

        # Step 3: Copy Orders
        bot_table.orders = []
        for order in getattr(bot, "orders", []):
            bot_table.orders.append(self._build_order_row(order))

        return bot_table

    def update_logs(
        self, log_message: str | list[str], bot: BotModel | BotTable
    ) -> BotTable:
        if not bot:
            raise BinbotErrors("Bot not found")

        ts = ts_to_humandate(ts=timestamp())

        with get_db_session(self._external_session) as s:
            # Get the managed bot instance from the session
            bot_row = s.get(BotTable, UUID(str(bot.id)))
            if not bot_row:
                raise BinbotErrors("Bot not found")

            if isinstance(log_message, list):
                new_logs = [f"[{ts}] {msg}" for msg in log_message]
                bot_row.logs = new_logs + (bot_row.logs or [])
            else:
                if bot_row.logs is None:
                    bot_row.logs = []
                bot_row.logs.append(f"[{ts}] {log_message}")

            flag_modified(bot_row, "logs")

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)
            s.expunge(bot_row)

            return bot_row

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        limit: int = 200,
        offset: int = 0,
        bot_name: str | None = None,
    ) -> Sequence[BotTable]:

        stmt = select(BotTable).options(
            selectinload(BOT_DEAL_REL),
            selectinload(BOT_ORDERS_REL),
            selectinload(BOT_RECOVERY_REL),
        )

        if status and status != Status.all:
            stmt = stmt.where(BotTable.status == status)

        if start_date:
            stmt = stmt.where(BotTable.created_at >= int(start_date))

        if end_date:
            stmt = stmt.where(BotTable.created_at <= int(end_date))

        if bot_name:
            bot_name = re.sub(r"[^\w\s\-']", "", bot_name.strip())
            stmt = stmt.where(BotTable.name == bot_name)

        stmt = (
            stmt.order_by(
                desc(BotTable.created_at),
                case((BotTable.status == Status.active, 1), else_=2),
                asc(BotTable.pair),
            )
            .limit(limit)
            .offset(offset)
        )

        with get_db_session(self._external_session) as s:
            bots = s.exec(stmt).unique().all()
            for bot in bots:
                detach_bot_graph(s, bot)
            return bots

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
        position: Position | None = None,
    ) -> BotTable:

        with get_db_session(self._external_session) as s:
            stmt = select(BotTable).options(
                selectinload(BOT_DEAL_REL),
                selectinload(BOT_ORDERS_REL),
                selectinload(BOT_RECOVERY_REL),
            )

            if bot_id:
                stmt = stmt.where(BotTable.id == UUID(bot_id))

            elif symbol:
                stmt = stmt.where(BotTable.pair == symbol)

                if status and status != Status.all:
                    stmt = stmt.where(BotTable.status == status)
                elif position:
                    stmt = stmt.where(BotTable.position == position)

            else:
                raise BinbotErrors("Invalid bot id or symbol")

            bot = s.exec(stmt).first()

            if not bot:
                raise BinbotErrors("Bot not found")

            detach_bot_graph(s, bot)
            return bot

    # --------------------------------------------------
    # Create / Save / Delete
    # --------------------------------------------------

    def create(self, data: BotBase) -> BotTable:
        new_bot = BotTable(
            **data.model_dump(exclude={"recovery_params"}),
            deal=DealTable(),
            orders=[],
        )
        if data.recovery_params is not None:
            new_bot.recovery_params = RecoveryBotTable(
                **data.recovery_params.model_dump()
            )

        with get_db_session(self._external_session) as s:
            s.add(new_bot)
            s.commit()
            s.refresh(new_bot)
            detach_bot_graph(s, new_bot)

        return new_bot

    def save(
        self,
        data: BotModel | BotTable,
        *,
        recovery_params_submitted: bool = False,
        recovery_params: RecoveryParams | None = None,
    ) -> BotTable:
        with get_db_session(self._external_session) as s:
            # Fetch the existing bot from DB (already attached to session)
            bot_row = s.get(BotTable, UUID(str(data.id)))
            if not bot_row:
                raise SaveBotError("Bot not found")

            if not bot_row.deal:
                raise SaveBotError("Bot must have associated deal")

            # Convert BotModel to BotTable if needed (detached)
            data_table = self.update_table(data)

            # Update scalar fields on the managed bot_row
            for field_name in BotTable.model_fields.keys():
                if field_name in {
                    "id",
                    "deal",
                    "orders",
                    "deal_id",
                    "recovery_mode_id",
                    "recovery_params",
                }:
                    continue
                if hasattr(data_table, field_name):
                    setattr(bot_row, field_name, getattr(data_table, field_name))

            if recovery_params_submitted:
                if recovery_params is None:
                    recovery_row = bot_row.recovery_params
                    bot_row.recovery_params = None
                    bot_row.recovery_mode_id = None
                    if recovery_row is not None:
                        s.delete(recovery_row)
                elif bot_row.recovery_params is None:
                    bot_row.recovery_params = RecoveryBotTable(
                        **recovery_params.model_dump()
                    )
                else:
                    for field_name in RecoveryParams.model_fields:
                        setattr(
                            bot_row.recovery_params,
                            field_name,
                            getattr(recovery_params, field_name),
                        )
                    bot_row.recovery_params.updated_at = timestamp()

            # Update deal fields (preserve existing deal.id)
            for field_name in DealTable.model_fields.keys():
                if field_name in {"id", "bot", "paper_trading"}:
                    continue
                if hasattr(data_table.deal, field_name):
                    setattr(
                        bot_row.deal, field_name, getattr(data_table.deal, field_name)
                    )

            # Sync orders
            for order_data in data_table.orders:
                existing = s.exec(
                    select(ExchangeOrderTable).where(
                        ExchangeOrderTable.order_id == str(order_data.order_id)
                    )
                ).first()

                if existing:
                    self._sync_order_fields(existing, order_data)
                else:
                    new_order = self._build_order_row(order_data, bot_id=bot_row.id)
                    s.add(new_order)

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)
            detach_bot_graph(s, bot_row)

            return bot_row

    def delete(self, bot_ids: List[str]) -> List[str]:
        with get_db_session(self._external_session) as s:
            for id_str in bot_ids:
                bot = s.get(BotTable, UUID(id_str))
                if bot:
                    s.delete(bot)
            s.commit()

        return bot_ids

    # --------------------------------------------------
    # Orders
    # --------------------------------------------------
    def get_order(self, order_id: str) -> ExchangeOrderTable:
        with get_db_session(self._external_session) as s:
            order = s.exec(
                select(ExchangeOrderTable).where(
                    ExchangeOrderTable.order_id == order_id
                )
            ).first()

            if not order:
                raise BinbotErrors("Order not found")

            s.expunge(order)
            return order

    def update_order(self, order: OrderModel) -> ExchangeOrderTable:
        with get_db_session(self._external_session) as s:
            existing = s.exec(
                select(ExchangeOrderTable).where(
                    ExchangeOrderTable.order_id == str(order.order_id)
                )
            ).first()

            if not existing:
                raise BinbotErrors("Order not found")

            self._sync_order_fields(existing, order)

            s.add(existing)
            s.commit()
            s.refresh(existing)
            s.expunge(existing)

            return existing

    def delete_order(self, order_id: str, bot_id: str | None = None) -> str:
        with get_db_session(self._external_session) as s:
            stmt = select(ExchangeOrderTable).where(
                ExchangeOrderTable.order_id == order_id
            )
            if bot_id:
                stmt = stmt.where(ExchangeOrderTable.bot_id == UUID(str(bot_id)))
            order = s.exec(stmt).first()

            if not order:
                raise BinbotErrors("Order not found")

            s.delete(order)
            s.commit()

        return str(order_id)

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def get_list_algo(self) -> list[AlgoRankingItem]:
        """
        Query all bots, group by name, and return a list of AlgoRankingItem
        with non-repeating bot names, their counts, and aggregated profit,
        ordered from highest bot_profit to lowest.
        """
        stmt = (
            select(
                BotTable.name,
                func.count(1).label("count"),
                func.coalesce(
                    func.sum(
                        (DealTable.closing_price - DealTable.opening_price)
                        / func.nullif(DealTable.opening_price, 0)
                    ),
                    0,
                ).label("bot_profit"),
            )
            .outerjoin(BOT_DEAL_REL)
            .group_by(BotTable.name)
            .order_by(desc("bot_profit"))
        )

        with get_db_session(self._external_session) as s:
            rows = s.exec(stmt).all()

        return [
            AlgoRankingItem(name=name, count=count, bot_profit=bot_profit)
            for name, count, bot_profit in rows
        ]

    def get_active_pairs(self) -> Sequence[str]:
        stmt = select(BotTable.pair).where(
            col(BotTable.status).in_(ACTIVE_BOT_STATUSES)
        )

        with get_db_session(self._external_session) as s:
            return s.exec(stmt).all()

    def get_active_for_symbol(
        self,
        symbol: str,
        market_type: Any | None = None,
    ) -> BotTable | None:
        stmt = (
            select(BotTable)
            .where(BotTable.pair == symbol)
            .where(col(BotTable.status).in_(ACTIVE_BOT_STATUSES))
            .options(selectinload(BOT_DEAL_REL))
            .options(selectinload(BOT_ORDERS_REL))
            .options(selectinload(BOT_RECOVERY_REL))
        )
        if market_type is not None:
            stmt = stmt.where(BotTable.market_type == market_type)

        with get_db_session(self._external_session) as s:
            bot = s.exec(stmt).first()
            if bot is not None:
                detach_bot_graph(s, bot)
            return bot
