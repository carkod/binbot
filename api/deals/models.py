from time import time

class OrderModel:
    def __init__(
        self,
        timestamp,
        order_id,
        pair,
        order_type,
        price,
        qty,
        fills,
        status,
        deal_type="base_order",
        order_side="BUY",
        time_in_force="GTC",
        *args,
        **kwargs
    ):
        self.order_type=order_type
        self.time_in_force=time_in_force
        self.timestamp=timestamp
        self.order_id=order_id
        self.order_side=order_side
        self.pair=pair
        self.fills=fills
        self.qty=float(qty)
        self.status=status
        self.price=float(price)
        self.deal_type=deal_type

class DealModel:
    def __init__(
        self,
        buy_price=0,
        buy_total_qty=0,
        buy_timestamp=time() * 1000,
        current_price=0,
        avg_buy_price=0,
        take_profit_price=0,
        sell_timestamp=time() * 1000,
        sell_price=0,
        sell_qty=0,
        trailling_stop_loss_price=0,
        stop_loss_price=0,
        trailling_profit=0,
        so_prices=0, # old
        post_closure_current_price=0, # old
        *args,
        **kwargs        
    ):
        self.avg_buy_price: float = float(avg_buy_price)
        self.buy_price: float = float(buy_price)
        self.buy_timestamp: float = buy_timestamp
        self.buy_total_qty: float = buy_total_qty
        self.current_price: float = float(current_price)
        self.sell_price: float = float(sell_price)
        self.sell_qty: float = float(sell_qty)
        self.sell_timestamp: float = sell_timestamp
        self.stop_loss_price: float = float(stop_loss_price)
        self.take_profit_price: float = float(take_profit_price)
        self.trailling_stop_loss_price: float = float(trailling_stop_loss_price)
        self.trailling_profit: float = float(trailling_profit)
        self.so_price = so_prices
        self.post_closure_current_price = post_closure_current_price
