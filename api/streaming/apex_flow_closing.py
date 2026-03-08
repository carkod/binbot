from pandas import Series
import numpy as np
from pybinbot import Indicators, KlineSchema
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from pandera.typing import DataFrame as TypedDataFrame


class ApexFlowClose:
    """
    Minimal ApexFlow for closing positions:
    - Provides detector flags for exit decisions
    - Provides trend EMA bias
    """

    def __init__(
        self, df: TypedDataFrame[KlineSchema], btc_df: TypedDataFrame[KlineSchema]
    ) -> None:
        self.exchange = AutotradeCrud().get_settings().exchange_id
        self.df = df
        self.btc_df = btc_df

    def compute_entry_expansion_range(self, bot: BotModel, lookahead: int = 3) -> float:
        entry_ts = bot.deal.opening_timestamp
        df = self.df

        # find index of entry candle
        entry_idx = df.index[df["timestamp"] >= entry_ts]

        if len(entry_idx) == 0:
            return 0.0

        start = entry_idx[0]
        window = df.loc[start : start + lookahead - 1]

        if window.empty:
            return 0.0

        return float(window["high"].max() - window["low"].min())

    # ------------------ Detectors ------------------ #
    def run_detectors(self) -> TypedDataFrame[KlineSchema]:
        df = self.df.copy()
        # --- VCE detector ---
        df = Indicators.atr(df, window=14, min_periods=14)

        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"].abs() + 1e-6)

        atr_threshold = df["ATR"].rolling(50, min_periods=50).quantile(0.25)
        compression = (df["bb_width"] < 0.04) & (df["ATR"] < atr_threshold)
        atr_mean = df["ATR"].rolling(20).mean()
        vol_mean = df["volume"].rolling(20).mean()
        expansion = (df["ATR"] > atr_mean * 1.5) & (df["volume"] > vol_mean * 1.3)
        df["vce_signal"] = expansion & compression.shift(1).rolling(3).max().astype(
            bool
        )

        # Direction (LONG/SHORT)
        vce_dir = Series(index=df.index, dtype=object)
        vce_dir[df["close"] > df["bb_upper"].shift(1)] = "LONG"
        vce_dir[df["close"] < df["bb_lower"].shift(1)] = "SHORT"
        df["vce_direction"] = vce_dir
        df.loc[~df["vce_signal"], "vce_direction"] = None

        # --- Momentum Continuation (MCD) ---
        df = Indicators.trend_ema(df)
        df = Indicators.rsi(df)
        momentum = (
            (df["close"] > df["ema_fast"])
            & (df["ema_fast"] > df["ema_slow"])
            & (df["rsi"] > 55)
        )
        atr_ok = df["ATR"] > df["ATR"].rolling(20).mean() * 1.2
        df["momentum_continue"] = momentum & atr_ok
        df["mcd_direction"] = np.where(df["ema_fast"] > df["ema_slow"], "LONG", "SHORT")
        df.loc[~df["momentum_continue"], "mcd_direction"] = None

        # --- LSR ---
        prev_high = df["high"].rolling(20).max().shift(1)
        prev_low = df["low"].rolling(20).min().shift(1)
        vol_mean = df["volume"].rolling(20).mean()
        sweep_high = (df["high"] > prev_high) & (df["close"] < prev_high)
        sweep_low = (df["low"] < prev_low) & (df["close"] > prev_low)
        volume_ok = df["volume"] > vol_mean * 1.8
        df["lsr_signal"] = (sweep_high | sweep_low) & volume_ok
        lsr_dir = Series(index=df.index, dtype=object)
        lsr_dir[sweep_low] = "LONG"
        lsr_dir[sweep_high] = "SHORT"
        df["lsr_direction"] = lsr_dir

        # --- LCRS (Low-Cap Relative Strength) ---
        if not self.btc_df.empty:
            asset_ret = df["close"].pct_change(20)
            btc_ret = self.btc_df["close"].pct_change(20)
            rel_strength_ma = (asset_ret / (btc_ret + 1e-9)).rolling(5).mean()
            df["lcrs_signal"] = rel_strength_ma > 1.02
        else:
            df["lcrs_signal"] = False

        return df

    # ------------------ Public API for closing ------------------ #
    def get_detectors(self) -> dict:
        """Return latest detector signals (True/False)"""
        self.run_detectors()

        if self.df.empty:
            return {"vce": False, "mcd": False, "lsr": False, "lcrs": False}
        last = self.df.iloc[-1]
        return {
            "vce": bool(last.get("vce_signal", False)),
            "mcd": bool(last.get("momentum_continue", False)),
            "lsr": bool(last.get("lsr_signal", False)),
            "lcrs": bool(last.get("lcrs_signal", False)),
        }

    def get_trend_ema(self) -> tuple[float, float]:
        """Return latest EMA fast/slow for trend bias"""
        if (
            self.df.empty
            or "ema_fast" not in self.df.columns
            or "ema_slow" not in self.df.columns
        ):
            return 0.0, 0.0
        last = self.df.iloc[-1]
        return float(last["ema_fast"]), float(last["ema_slow"])
