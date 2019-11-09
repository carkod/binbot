import pytest

from app.utilities.get_data import Exchange_Info

from .new_order import BUY_ORDER

ei = Exchange_Info()
data = ei.request_data()

def test_quantity():
    new_order = BUY_ORDER('BNBBTC')
    assert new_order.compute_quantity() == int(new_order.compute_quantity())
    assert new_order.compute_quantity() == abs(new_order.compute_quantity())
    assert new_order.compute_quantity() > 0
    assert new_order.compute_quantity() < 99999
