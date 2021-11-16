from datetime import datetime, timedelta

import pandas as pd
from api.apis import BinanceApi
from api.tools.handle_error import (
    jsonResp,
    jsonResp_error_message,
)
from flask import request


class Candlestick(BinanceApi):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def _candlestick_request(self, params=None):
        pair = request.view_args.get("pair")
        interval = request.view_args.get("interval")

        # 200 limit + 100 Moving Average = 300
        limit = request.view_args.get("limit") or 300
        if not params:
            params = {"symbol": pair, "interval": interval, "limit": limit}
        data = self.request(url=self.candlestick_url, params=params)
        if data:
            df = pd.DataFrame(data)
            dates = df[0].tolist()
        else:
            df = []
            dates = []

        return df, dates

    def candlestick_trace(self, df, dates):
        close = df[4].tolist()
        high = df[2].tolist()
        low = df[3].tolist()
        open = df[1].tolist()
        defaults = {
            "x": dates,
            "close": close,
            "high": high,
            "low": low,
            "open": open,
            "decreasing": {"line": {"color": "red"}},
            "increasing": {"line": {"color": "green"}},
            "line": {"color": "#17BECF"},
            "type": "candlestick",
            "xaxis": "x",
            "yaxis": "y",
        }
        return defaults

    def bollinguer_bands(self, df, dates):
        # 200 limit + 100 ma
        data = df[4]

        kline_df_100 = (
            data.rolling(window=100)
            .mean()
            .dropna()
            .reset_index(drop=True)
            .values.tolist()
        )
        kline_df_25 = (
            data.rolling(window=25)
            .mean()
            .dropna()
            .reset_index(drop=True)
            .values.tolist()
        )
        kline_df_7 = (
            data.rolling(window=7)
            .mean()
            .dropna()
            .reset_index(drop=True)
            .values.tolist()[94:]
        )

        ma_100 = {
            "x": dates,
            "y": kline_df_100,
            "line": {"color": "#9368e9"},
            "type": "scatter",
        }
        ma_25 = {
            "x": dates,
            "y": kline_df_25,
            "line": {"color": "#fb404b"},
            "type": "scatter",
        }
        ma_7 = {
            "x": dates,
            "y": kline_df_7,
            "line": {"color": "#ffa534"},
            "type": "scatter",
        }

        return ma_100, ma_25, ma_7

    def get(self):
        """
        Get candlestick graph data
        Index 0: trace
        Index 1: ma_100
        Index 2: ma_25
        Index 3: ma_7
        """
        pair = request.view_args.get("pair")
        interval = request.view_args.get("interval")
        stats = request.view_args.get("stats")

        if not pair:
            return jsonResp_error_message("Symbol/Pair is required")
        if not interval:
            return jsonResp_error_message("Provide a candlestick interval")

        # 200 limit + 100 Moving Average = 300
        limit = request.view_args.get("limit") or 300

        df, dates = self._candlestick_request()
        if len(dates) == 0:
            return jsonResp_error_message("There is not enough data for this symbol")
        trace = self.candlestick_trace(df, dates)
        ma_100, ma_25, ma_7 = self.bollinguer_bands(df, dates)
        if stats:
            df["candle_spread"] = abs(pd.to_numeric(df[1]) - pd.to_numeric(df[4]))
            curr_candle_spread = df["candle_spread"][df.shape[0] - 1]
            avg_candle_spread = df["candle_spread"].median()

            df["volume_spread"] = abs(pd.to_numeric(df[1]) - pd.to_numeric(df[4]))
            curr_volume_spread = df["volume_spread"][df.shape[0] - 1]
            avg_volume_spread = df["volume_spread"].median()

            high_price = max(df[2])
            low_price = max(df[3])
            amplitude = (float(high_price) / float(low_price)) - 1

            all_time_low = pd.to_numeric(df[3]).min()
            resp = jsonResp(
                {
                    "trace": [trace, ma_100, ma_25, ma_7],
                    "interval": interval,
                    "curr_candle_spread": curr_candle_spread,
                    "avg_candle_spread": avg_candle_spread,
                    "curr_volume_spread": curr_volume_spread,
                    "avg_volume_spread": avg_volume_spread,
                    "amplitude": amplitude,
                    "all_time_low": all_time_low,
                }
            )
            return resp
        else:
            resp = jsonResp(
                {"trace": [trace, ma_100, ma_25, ma_7], "interval": interval}, 200
            )
            return resp

    def get_diff(self):
        """To be removed after dashboard refactor"""
        today = datetime.today()
        first = today.replace(day=1)
        lastMonth = first - timedelta(days=1)
        # One month from today
        first_lastMonth = today - timedelta(days=lastMonth.day)
        startTime = int(round(first_lastMonth.timestamp() * 1000))

        params = {
            "symbol": pair,
            "interval": interval,
            "limit": lastMonth.day,
            "startTime": startTime,
        }
        df, dates = self._candlestick_request(params)

        # New df with dates and close
        df_new = df[[0, 3]]
        df_new[3].astype(float)
        close_prices = df_new[3].astype(float).pct_change().iloc[1:].values.tolist()
        dates = df_new[0].iloc[1:].values.tolist()
        trace = {
            "x": dates,
            "y": close_prices,
            "type": "scatter",
            "mode": "lines+markers",
        }
        resp = jsonResp({"message": "Successfully retrieved data", "data": trace})
        return resp
