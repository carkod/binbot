import numpy as np
import pandas as pd
from pydantic import BaseModel
from tools.maths import round_numbers


class VolatilityMetrics(BaseModel):
    returns_std: float
    price_range_ratio: float
    quantile_90: float
    quantile_75: float
    quantile_25: float
    quantile_10: float
    adaptive_stop_loss: float
    adaptive_trailing_deviation: float
    confidence_score: float


class QuantileVolatilityCalculator:
    def __init__(self, lookback_periods=50, min_periods=10):
        self.lookback_periods = lookback_periods
        self.min_periods = min_periods

    def calculate_returns_volatility(self, prices: pd.Series):
        log_returns = np.log(prices / prices.shift(1)).dropna()
        return {
            "returns_std": float(log_returns.std()),
            "returns_var": float(log_returns.var()),
            "returns_mean": float(log_returns.mean()),
        }

    def calculate_price_range_volatility(self, klines_data):
        df = pd.DataFrame(
            klines_data,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
            ],
        )
        df["range_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["true_range"] = df[["high", "low", "close"]].max(axis=1) - df[
            ["high", "low", "close"]
        ].min(axis=1)
        return {
            "range_ratio_mean": float(df["range_ratio"].mean()),
            "range_ratio_std": float(df["range_ratio"].std()),
            "true_range_mean": float(df["true_range"].mean()),
            "true_range_std": float(df["true_range"].std()),
        }

    def calculate_quantile_levels(self, vol_data: pd.Series):
        quantiles = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
        quantile_values = {
            f"q{int(q * 100)}": float(vol_data.quantile(q)) for q in quantiles
        }
        return quantile_values

    def adaptive_stop_loss_calculation(
        self,
        prices: pd.Series,
        base_stop_loss: float = 3.0,
        volatility_multiplier: float = 1.5,
    ) -> VolatilityMetrics:
        if len(prices) < self.min_periods:
            return VolatilityMetrics(
                returns_std=0,
                price_range_ratio=0,
                quantile_90=0,
                quantile_75=0,
                quantile_25=0,
                quantile_10=0,
                adaptive_stop_loss=base_stop_loss,
                adaptive_trailing_deviation=base_stop_loss * 0.8,
                confidence_score=0.3,
            )
        log_returns = np.log(prices / prices.shift(1)).dropna()
        returns_std = float(log_returns.std())
        rolling_vol = (
            log_returns.rolling(window=min(20, len(log_returns) // 2)).std().dropna()
        )
        if len(rolling_vol) < 5:
            return VolatilityMetrics(
                returns_std=returns_std,
                price_range_ratio=0,
                quantile_90=0,
                quantile_75=0,
                quantile_25=0,
                quantile_10=0,
                adaptive_stop_loss=base_stop_loss,
                adaptive_trailing_deviation=base_stop_loss * 0.8,
                confidence_score=0.3,
            )
        quantile_metrics = self.calculate_quantile_levels(rolling_vol)
        current_vol = rolling_vol.iloc[-1] if len(rolling_vol) > 0 else returns_std
        current_percentile = (rolling_vol <= current_vol).mean()
        volatility_90th = quantile_metrics.get("q90", returns_std)
        volatility_75th = quantile_metrics.get("q75", returns_std)
        vol_90_pct = volatility_90th * 100 * volatility_multiplier
        vol_75_pct = volatility_75th * 100 * volatility_multiplier
        current_vol = rolling_vol.iloc[-1] if len(rolling_vol) > 0 else returns_std
        current_percentile = (rolling_vol <= current_vol).mean()

        # Adaptive stop loss calculation based on volatility quantiles
        # Use 90th percentile as a measure of extreme volatility
        volatility_90th = quantile_metrics.get("q90", returns_std)
        volatility_75th = quantile_metrics.get("q75", returns_std)

        # Convert volatility to percentage terms
        vol_90_pct = volatility_90th * 100 * volatility_multiplier
        vol_75_pct = volatility_75th * 100 * volatility_multiplier

        # Adaptive stop loss logic
        if current_percentile >= 0.9:
            # Very high volatility - use wider stop loss
            adaptive_stop_loss = max(base_stop_loss, min(vol_90_pct, 8.0))
            adaptive_trailing = max(base_stop_loss * 0.6, min(vol_75_pct, 6.0))
        elif current_percentile >= 0.75:
            # High volatility
            adaptive_stop_loss = max(base_stop_loss, min(vol_75_pct, 6.0))
            adaptive_trailing = max(base_stop_loss * 0.7, min(vol_75_pct * 0.8, 4.5))
        elif current_percentile <= 0.25:
            # Low volatility - can use tighter stop loss
            adaptive_stop_loss = max(base_stop_loss * 0.7, 1.5)
            adaptive_trailing = max(base_stop_loss * 0.5, 1.0)
        else:
            # Normal volatility
            adaptive_stop_loss = base_stop_loss
            adaptive_trailing = base_stop_loss * 0.8

        # Calculate price range ratio for additional context
        price_changes = (prices.pct_change().abs() * 100).dropna()
        price_range_ratio = (
            float(price_changes.quantile(0.9)) if len(price_changes) > 0 else 0
        )

        # Confidence score based on data quality
        confidence_score = min(len(prices) / self.lookback_periods, 1.0) * 0.7 + (
            0.3 if len(rolling_vol) >= 10 else 0.1
        )

        return VolatilityMetrics(
            returns_std=returns_std,
            price_range_ratio=price_range_ratio,
            quantile_90=float(quantile_metrics.get("q90", 0)),
            quantile_75=float(quantile_metrics.get("q75", 0)),
            quantile_25=float(quantile_metrics.get("q25", 0)),
            quantile_10=float(quantile_metrics.get("q10", 0)),
            adaptive_stop_loss=round_numbers(adaptive_stop_loss, 2),
            adaptive_trailing_deviation=round_numbers(adaptive_trailing, 2),
            confidence_score=round_numbers(confidence_score, 2),
        )

    def get_market_regime(self, prices: pd.Series) -> str:
        """
        Determine market regime based on volatility patterns.

        Args:
            prices: Series of closing prices

        Returns:
            Market regime: 'high_vol', 'normal_vol', 'low_vol'
        """
        if len(prices) < self.min_periods:
            return "unknown"

        log_returns = np.log(prices / prices.shift(1)).dropna()
        rolling_vol = log_returns.rolling(window=20).std().dropna()

        if len(rolling_vol) < 5:
            return "unknown"

        current_vol = rolling_vol.iloc[-1]
        vol_75th = rolling_vol.quantile(0.75)
        vol_25th = rolling_vol.quantile(0.25)

        if current_vol >= vol_75th:
            return "high_vol"
        elif current_vol <= vol_25th:
            return "low_vol"
        else:
            return "normal_vol"
