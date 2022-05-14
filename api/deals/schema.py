def DealSchema():
    """
    To become a proper class with validations in the future
    """
    return {
        "last_order_id": 0,
        "buy_timestamp": 0,
        "buy_price": "",
        "buy_total_qty": "",
        "current_price": "",
        "take_profit_price": "",
        "so_prices": [],
        "sell_timestamp": 0,
        "sell_price": "",
        "sell_qty": "",
        "post_closure_current_price": "",
    }
