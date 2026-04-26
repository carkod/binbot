from unittest.mock import patch


def test_apply_and_get_active_threshold_override(client):
    apply_payload = {
        "recommendation": {
            "strategy": "coinrule_grid_trading",
            "symbol": "XBTUSDTM",
            "buy_trigger_pct": 0.016,
            "sell_trigger_pct": 0.02,
            "ttl_minutes": 60,
            "confidence": 0.72,
            "reason": "Range regime with compressed volatility.",
            "profile": "tight_range",
        },
        "source_provider": "manual",
        "market_context_timestamp": 1700000000,
        "raw_model_response": {"type": "manual"},
    }

    apply_response = client.post(
        "/strategy-threshold-overrides/apply", json=apply_payload
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["error"] == 0

    active_response = client.get(
        "/strategy-threshold-overrides/active",
        params={"strategy_name": "coinrule_grid_trading", "symbol": "XBTUSDTM"},
    )
    assert active_response.status_code == 200
    assert active_response.json()["error"] == 0
    assert active_response.json()["data"]["buy_trigger_pct"] == 0.016


def test_suggest_override_applies_when_guardrails_pass(client):
    suggestion_payload = {
        "strategy": "coinrule_grid_trading",
        "symbol": "XBTUSDTM",
        "market_context": {
            "market_regime": "RANGE",
            "coin_regime": "RANGE",
            "market_stress_score": 0.2,
            "atr_pct": 0.01,
            "bb_width": 0.02,
        },
        "model": "gpt-4.1-mini",
        "apply": True,
    }

    with patch(
        "strategy_thresholds.routes.OpenAiThresholdAdvisor.suggest",
        return_value=(
            {
                "strategy": "coinrule_grid_trading",
                "symbol": "XBTUSDTM",
                "buy_trigger_pct": 0.018,
                "sell_trigger_pct": 0.021,
                "ttl_minutes": 60,
                "confidence": 0.8,
                "reason": "RANGE market and stable volatility.",
                "profile": "balanced_range",
            },
            {"provider": "openai"},
        ),
    ):
        response = client.post(
            "/strategy-threshold-overrides/suggest", json=suggestion_payload
        )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] == 0
    assert body["data"]["profile"] == "balanced_range"

    list_response = client.get(
        "/strategy-threshold-overrides",
        params={"strategy_name": "coinrule_grid_trading", "symbol": "XBTUSDTM"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) >= 1


def test_suggest_override_rejects_high_stress(client):
    suggestion_payload = {
        "strategy": "coinrule_grid_trading",
        "symbol": "XBTUSDTM",
        "market_context": {
            "market_regime": "RANGE",
            "coin_regime": "RANGE",
            "market_stress_score": 0.45,
        },
        "apply": False,
    }

    with patch(
        "strategy_thresholds.routes.OpenAiThresholdAdvisor.suggest",
        return_value=(
            {
                "strategy": "coinrule_grid_trading",
                "symbol": "XBTUSDTM",
                "buy_trigger_pct": 0.018,
                "sell_trigger_pct": 0.021,
                "ttl_minutes": 60,
                "confidence": 0.8,
                "reason": "RANGE market and stable volatility.",
                "profile": "balanced_range",
            },
            {"provider": "openai"},
        ),
    ):
        response = client.post(
            "/strategy-threshold-overrides/suggest", json=suggestion_payload
        )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] == 1
    assert "market stress too high" in body["message"]
