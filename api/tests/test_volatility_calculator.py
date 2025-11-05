import pandas as pd
import numpy as np
from streaming.volatility_calculator import (
    QuantileVolatilityCalculator,
    VolatilityMetrics,
)


class TestQuantileVolatilityCalculator:
    """Test cases for QuantileVolatilityCalculator"""

    def setup_method(self):
        """Setup test data"""
        self.calculator = QuantileVolatilityCalculator(
            lookback_periods=50, min_periods=10
        )
        np.random.seed(42)
        n_periods = 100
        base_price = 100
        returns = []
        for i in range(n_periods):
            if i < 30:
                vol = 0.01
            elif i < 60:
                vol = 0.04
            else:
                vol = 0.02
            ret = np.random.normal(0, vol)
            returns.append(ret)
        log_prices = np.cumsum(returns)
        self.prices = pd.Series(base_price * np.exp(log_prices))
        self.klines_data = []
        for i, price in enumerate(self.prices):
            high = price * (1 + abs(returns[i]))
            low = price * (1 - abs(returns[i]))
            open_price = price * (1 + returns[i] * 0.5)
            self.klines_data.append(
                [
                    i * 1000,  # timestamp
                    open_price,
                    high,
                    low,
                    price,
                    1000,  # volume
                    (i + 1) * 1000,  # close_time
                ]
            )

    def test_calculate_returns_volatility(self):
        result = self.calculator.calculate_returns_volatility(self.prices)
        assert "returns_std" in result
        assert "returns_var" in result
        assert "returns_mean" in result
        assert result["returns_std"] > 0
        assert result["returns_var"] > 0

    def test_calculate_price_range_volatility(self):
        result = self.calculator.calculate_price_range_volatility(self.klines_data)
        assert "range_ratio_mean" in result
        assert "range_ratio_std" in result
        assert "true_range_mean" in result
        assert "true_range_std" in result
        assert result["range_ratio_mean"] >= 0
        assert result["true_range_mean"] >= 0

    def test_calculate_quantile_levels(self):
        vol_data = pd.Series(np.random.uniform(0.01, 0.05, 50))
        result = self.calculator.calculate_quantile_levels(vol_data)
        expected_keys = ["q10", "q25", "q50", "q75", "q90", "q95"]
        for key in expected_keys:
            assert key in result
        assert result["q10"] <= result["q25"]
        assert result["q25"] <= result["q50"]
        assert result["q50"] <= result["q75"]
        assert result["q75"] <= result["q90"]
        assert result["q90"] <= result["q95"]

    def test_adaptive_stop_loss_calculation(self):
        result = self.calculator.adaptive_stop_loss_calculation(
            prices=self.prices, base_stop_loss=3.0
        )
        assert isinstance(result, VolatilityMetrics)
        assert result.adaptive_stop_loss > 0
        assert result.adaptive_trailing_deviation > 0
        assert result.confidence_score >= 0
        assert result.confidence_score <= 1.0
        assert 1.0 <= result.adaptive_stop_loss <= 10.0
        assert 0.5 <= result.adaptive_trailing_deviation <= 8.0

    def test_get_market_regime(self):
        regime = self.calculator.get_market_regime(self.prices)
        assert regime in ["high_vol", "normal_vol", "low_vol", "unknown"]

    def test_insufficient_data_handling(self):
        short_prices = pd.Series([100, 101, 102])
        result = self.calculator.adaptive_stop_loss_calculation(prices=short_prices)
        assert result.confidence_score == 0.3
        assert result.adaptive_stop_loss == 3.0

    def test_volatility_regime_adaptation(self):
        low_vol_prices = pd.Series(
            [100 + i * 0.1 + np.random.normal(0, 0.005) for i in range(50)]
        )
        low_vol_result = self.calculator.adaptive_stop_loss_calculation(
            prices=low_vol_prices
        )
        high_vol_prices = pd.Series(
            [100 + i * 0.1 + np.random.normal(0, 0.03) for i in range(50)]
        )
        high_vol_result = self.calculator.adaptive_stop_loss_calculation(
            prices=high_vol_prices
        )
        assert (
            high_vol_result.adaptive_stop_loss
            >= low_vol_result.adaptive_stop_loss * 0.8
        )
