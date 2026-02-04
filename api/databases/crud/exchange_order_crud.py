from databases.tables.order_table import ExchangeOrderTable
from pybinbot import OrderStatus, BinbotErrors
from databases.utils import independent_session
from sqlmodel import select, Session


class ExchangeOrderTableCrud:
    """
    CRUD and database operations for the SQL API DB
    exchange_order table by order_id
    """

    def __init__(
        self,
        session: Session | None = None,
    ):
        if session is None:
            session = independent_session()
        self.session = session

    def get_by_order_id(
        self,
        order_id: str,
    ) -> ExchangeOrderTable:
        """
        Get one single order by order_id
        """
        statement = select(ExchangeOrderTable).where(
            ExchangeOrderTable.order_id == order_id
        )

        order = self.session.exec(statement).first()
        if not order:
            raise BinbotErrors(f"Order with id {order_id} not found")

        self.session.close()
        return order

    def update_one(
        self,
        order_id: str,
        filled_qty: float,
        price: float,
        order_time: int,
        status: OrderStatus = OrderStatus.FILLED,
        side: str | None = None,
    ) -> ExchangeOrderTable:
        """
        Update an existing exchange order record by order_id
        """
        statement = select(ExchangeOrderTable).where(
            ExchangeOrderTable.order_id == order_id
        )
        order = self.session.exec(statement).first()
        if not order:
            raise BinbotErrors(f"Order with id {order_id} not found")

        order.status = status
        order.qty = filled_qty
        order.price = price
        order.order_side = side if side is not None else order.order_side
        order.timestamp = order_time

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        self.session.close()
        return order
