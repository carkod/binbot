# allows us to use annotations without circular imports
from __future__ import annotations

from typing import TypeGuard

import pandas as pd


class OHLCDataFrame(pd.DataFrame):
    """DataFrame subclass marking validated OHLC + extended market columns.

    Provides class methods to (a) validate & coerce a generic DataFrame into an
    OHLCDataFrame and (b) act as a type guard for flow-sensitive typing.

    Required columns are kept in the explicit order requested by the user.

    Originally from binquant/shared/ohlc.py
    """

    REQUIRED_COLUMNS = [
        "open",
        "high",
        "low",
        "close",
        "open_time",
        "close_time",
        "volume",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
    ]

    # Preserve subclass through pandas operations when possible.
    @property
    def _constructor(self):
        return OHLCDataFrame

    @classmethod
    def is_ohlc_dataframe(cls, df: pd.DataFrame) -> TypeGuard[OHLCDataFrame]:
        """Return True if all required columns are present.

        This does *not* guarantee dtypes—only presence. Use `ensure_ohlc` for
        full validation + coercion.
        """
        return set(cls.REQUIRED_COLUMNS).issubset(df.columns)

    @classmethod
    def ensure_ohlc(cls, df: pd.DataFrame) -> OHLCDataFrame:
        """Validate & coerce a DataFrame into an OHLCDataFrame.

        Steps:
        - Verify all REQUIRED_COLUMNS are present (raises ValueError if missing).
        - Coerce numeric columns (including *_time which are expected as ms epoch).
        - Perform early failure if quote_asset_volume becomes entirely NaN.
        - Return the same underlying object cast to OHLCDataFrame (no deep copy).
        """
        missing = set(cls.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required OHLC columns: {missing}")

        numeric_cols = [
            "open",
            "high",
            "low",
            "close",
            "open_time",
            "close_time",
            "volume",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
        ]
        for col in numeric_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if (
            "quote_asset_volume" in df.columns
            and df["quote_asset_volume"].notna().sum() == 0
        ):
            raise ValueError(
                "quote_asset_volume column is entirely non-numeric after coercion; cannot compute quote_volume_ratio"
            )

        if not isinstance(df, OHLCDataFrame):
            df = OHLCDataFrame(df)
        return df


class HeikinAshi:
    """
    Heikin Ashi candle transformation.

    Canonical formulas applied to OHLC data:
        HA_Close = (O + H + L + C) / 4
        HA_Open  = (prev_HA_Open + prev_HA_Close) / 2, seed = (O0 + C0) / 2
        HA_High  = max(H, HA_Open, HA_Close)
        HA_Low   = min(L, HA_Open, HA_Close)

    This version:
      * Works if a 'timestamp' column exists (sorted chronologically first).
      * Does NOT mutate the original dataframe in-place; returns a copy.
      * Validates required columns.
    """

    @staticmethod
    def get_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        # Validate & coerce using the new type guard helper.
        df = OHLCDataFrame.ensure_ohlc(df)
        work = df.reset_index(drop=True).copy()

        # Compute HA_Close from ORIGINAL OHLC (still intact in 'work').
        # Ensure numeric dtypes (API feeds sometimes deliver strings)
        ohlc_cols = ["open", "high", "low", "close"]
        for c in ohlc_cols:
            # Only attempt conversion if dtype is not already numeric
            if not pd.api.types.is_numeric_dtype(work[c]):
                work.loc[:, c] = pd.to_numeric(work[c], errors="coerce")

        if work[ohlc_cols].isna().any().any():
            # Drop rows that became NaN after coercion (invalid numeric data)
            work = work.dropna(subset=ohlc_cols).reset_index(drop=True)
            if work.empty:
                raise ValueError("All OHLC rows became NaN after numeric coercion.")

        ha_close = (work["open"] + work["high"] + work["low"] + work["close"]) / 4.0

        # Seed HA_Open with original O & C (not HA close).
        ha_open = ha_close.copy()
        ha_open.iloc[0] = (work["open"].iloc[0] + work["close"].iloc[0]) / 2.0
        for i in range(1, len(work)):
            ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

        # High / Low derived from max/min of (raw high/low, ha_open, ha_close)
        ha_high = pd.concat([work["high"], ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([work["low"], ha_open, ha_close], axis=1).min(axis=1)

        # Assign transformed values.
        work.loc[:, "open"] = ha_open
        work.loc[:, "high"] = ha_high
        work.loc[:, "low"] = ha_low
        work.loc[:, "close"] = ha_close

        return work
