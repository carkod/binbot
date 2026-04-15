from copy import deepcopy

from bots.models import BotModel


mock_deal_data = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "base_order_size": 15.0,
    "current_price": 0.0,
    "take_profit_price": 0.0,
    "trailing_stop_loss_price": 0.0,
    "trailing_profit_price": 0.0,
    "stop_loss_price": 0.0,
    "total_interests": 0.0,
    "total_commissions": 0.0,
    "margin_loan_id": 0,
    "margin_repay_id": 0,
    "opening_price": 0.0,
    "opening_qty": 0.0,
    "opening_timestamp": 0,
    "closing_price": 0.0,
    "closing_qty": 0.0,
    "closing_timestamp": 0,
}

mock_bot_data = {
    "id": "cff9e468-87ee-46fa-8678-17af132b8434",
    "pair": "ADXUSDC",
    "fiat": "USDC",
    "quote_asset": "USDC",
    "fiat_order_size": 15.0,
    "candlestick_interval": "15m",
    "close_condition": "dynamic_trailing",
    "cooldown": 360,
    "created_at": 1733973560249.0,
    "updated_at": 1733973560249.0,
    "dynamic_trailing": False,
    "logs": [],
    "mode": "manual",
    "name": "Test bot 1",
    "status": "inactive",
    "stop_loss": 3.0,
    "margin_short_reversal": False,
    "take_profit": 2.3,
    "trailing": True,
    "trailing_deviation": 3.0,
    "trailing_profit": 0.0,
    "strategy": "long",
    "orders": [],
    "deal": mock_deal_data,
}

mock_bot_data_active = {
    "id": "ebda4958-837c-4544-bf97-9bf449698152",
    "pair": "ADAUSDC",
    "fiat": "USDC",
    "quote_asset": "USDC",
    "fiat_order_size": 25.0,
    "candlestick_interval": "15m",
    "close_condition": "dynamic_trailing",
    "cooldown": 360,
    "created_at": 1733973560249.0,
    "updated_at": 1733973560249.0,
    "dynamic_trailing": False,
    "logs": [],
    "mode": "manual",
    "name": "Test bot 3",
    "status": "active",
    "stop_loss": 3.0,
    "margin_short_reversal": False,
    "take_profit": 2.3,
    "trailing": True,
    "trailing_deviation": 3.0,
    "trailing_profit": 0.0,
    "strategy": "long",
    "orders": [],
    "deal": mock_deal_data,
}

mock_bot_data_superusdt = {
    "pair": "SUPERUSDT",
    "fiat": "USDC",
    "quote_asset": "USDC",
    "fiat_order_size": 15.0,
    "candlestick_interval": "15m",
    "close_condition": "dynamic_trailing",
    "cooldown": 360,
    "created_at": 1733973560249.0,
    "updated_at": 1733973560249.0,
    "dynamic_trailing": False,
    "logs": [],
    "mode": "manual",
    "name": "Test bot 1",
    "status": "inactive",
    "stop_loss": 3.0,
    "margin_short_reversal": False,
    "take_profit": 2.3,
    "trailing": True,
    "trailing_deviation": 3.0,
    "trailing_profit": 0.0,
    "strategy": "long",
    "orders": [],
    "deal": mock_deal_data,
}


def _build_bot_model(payload: dict) -> BotModel:
    """Create an isolated BotModel from a raw payload for tests."""
    return BotModel.model_validate(deepcopy(payload))


def make_mock_bot_model() -> BotModel:
    return _build_bot_model(mock_bot_data)


def make_mock_bot_active_model() -> BotModel:
    return _build_bot_model(mock_bot_data_active)


def make_mock_bot_superusdt_model() -> BotModel:
    return _build_bot_model(mock_bot_data_superusdt)
