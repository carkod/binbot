from datetime import datetime, timedelta
from multiprocessing.sharedctypes import Value
from numpy import number

import pandas as pd
from api.apis import BinbotApi
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from flask import request, current_app
from typing import TypedDict
from api.tools.round_numbers import round_numbers
from pymongo.errors import DuplicateKeyError


class KlinesParams(TypedDict):
    symbol: str
    interval: str
    limit: int


class KlinesSchema:
    def __init__(self, pair, interval=None, data=None, limit=300) -> None:
        self._id = pair  # pair
        self.interval = interval
        self.data: list = data
        self.limit = limit

    def create(self):
        try:
            result = current_app.db.klines.insert_one(
                {"_id": self._id, "interval": self.interval, "data": self.data}
            )
            return result
        except Exception as e:
            return e

    def update_data(self, timestamp):
        """
        Function that specifically updates candlesticks.
        Finds existence of candlesticks and then updates with new stream kline data or adds new data
        """
        new_data = self.data  # This is not existent data but stream data from API
        try:
            kline = current_app.db.klines.find_one({"_id": self._id})
            curr_ts = kline["data"][len(kline["data"]) - 1][0]
            if curr_ts == timestamp:
                # If found timestamp match - update
                update_kline = current_app.db.klines.update_one(
                    {"_id": self._id},
                    {"$push": {"data": {"$each": [new_data], "$slice": -1}}},
                )
            else:
                # If no timestamp match - push
                update_kline = current_app.db.klines.update_one(
                    {"_id": self._id},
                    {
                        "$push": {
                            "data": {
                                "$each": [new_data],
                            }
                        }
                    },
                )

            return update_kline
        except Exception as e:
            return e

    def delete_klines(self):
        result = current_app.db.klines.delete_one({"_id": self._id})
        return result


class Candlestick(BinbotApi):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def get_klines(self, binance=False, json=True, params: KlinesParams = None):
        """
        Servers 2 purposes:
        - Endpoint, json=True. @input params as request.args
        - Method returning dataframe and list of dates. @input params arg
        """
        symbol = request.args.get("symbol")
        interval = request.args.get("interval", "15m")
        # 200 limit + 100 Moving Average = 300
        limit = request.args.get("limit", 300)
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")

        if not symbol:
            return jsonResp_error_message("Symbol parameter is required")

        if not params:
            params: KlinesParams = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "startTime": start_time,
                "endTime": end_time,
            }

        if binance and not json:
            klines = self.request(url=self.candlestick_url, params=params)
            df = pd.DataFrame(klines)
            dates = df[0].tolist()
            return df, dates

        klines = current_app.db.klines.find_one({"_id": params["symbol"]})
        if not klines:
            try:
                # Store more data for db to fill up candlestick charts
                params["limit"] = 600
                data = self.request(url=self.candlestick_url, params=params)
                if "message" in data:
                    raise Exception(data["message"])
                KlinesSchema(params["symbol"], params["interval"], data).create()
                klines = current_app.db.klines.find_one({"_id": params["symbol"]})
            except DuplicateKeyError:
                resp = jsonResp_error_message(f"Duplicate key {params['symbol']}")
                return resp
            except Exception as e:
                return jsonResp_error_message(f"Error creating klines: {e}")

        if not json:
            if klines:
                df = pd.DataFrame(klines["data"])
                dates = df[0].tolist()
            else:
                df = []
                dates = []
            return df, dates

        resp = jsonResp(
            {
                "message": "Successfully retrieved candlesticks",
                "data": str(klines["data"]),
            }
        )
        return resp

    def update_klines(self):

        stream_data = request.json.get("data")
        pair = request.json.get("symbol")
        interval = request.json.get("interval")
        limit = request.json.get("limit", 300)

        # Map stream to kline
        # It must be in this order to match historical klines
        data = [
            stream_data["t"],
            stream_data["o"],
            stream_data["h"],
            stream_data["l"],
            stream_data["c"],
            stream_data["v"],
            stream_data["T"],
            stream_data["q"],
            stream_data["n"],
            stream_data["V"],
            stream_data["Q"],
            stream_data["B"],
        ]
        result = KlinesSchema(pair, interval, data, limit).update_data(stream_data["t"])
        if result:
            return jsonResp_message("Successfully updated candlestick data!")
        else:
            return jsonResp_error_message(
                f"Failed to update candlestick data: {result}"
            )

    def delete_klines(self):
        symbol = request.args.get("symbol")
        try:
            KlinesSchema(symbol).delete_klines()
            return jsonResp_message("Successfully deleted klines")
        except Exception as error:
            return jsonResp_error_message(f"Failed deleting klines {symbol}: {error}")

    def candlestick_trace(self, df, dates):
        """
        Create candlestick trace for plotly library
        - Cut off first 100 for MA_100
        - Return data as lists with the correct format (defaults)
        """
        # create lists for plotly
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
        """
        Create Moving Averages (MAs) in plotly format
        """
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
            .values.tolist()
        )

        ma_100 = {
            "x": dates[99:],
            "y": kline_df_100,
            "line": {"color": "#9368e9"},
            "type": "scatter",
        }
        ma_25 = {
            "x": dates[24:],
            "y": kline_df_25,
            "line": {"color": "#fb404b"},
            "type": "scatter",
        }
        ma_7 = {
            "x": dates[6:],
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

        @json:
        {
            "pair": string,
            "interval": string,
            "stats": boolean, Additional statistics such as MA, amplitude, volume, candle spreads
            "binance": boolean, whether to directly pull data from binance or from DB
            "limit": int,
            "start_time": int
            "end_time": int
        }
        """
        symbol = request.args.get("symbol")
        interval = request.args.get("interval")
        stats = request.args.get("stats", False)
        # 200 limit + 100 Moving Average = 300
        limit = request.args.get("limit", 300)
        binance = request.args.get("binance", False)
        start_time = request.args.get("start_time", type=int)
        end_time = request.args.get("end_time", type=int)

        if not symbol:
            return jsonResp_error_message("Symbol is required")
        if not interval:
            return jsonResp_error_message("Provide a candlestick interval")

        df, dates = self.get_klines(
            binance=binance,
            json=False,
            params={
                "limit": limit,
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time, # starTime and endTime must be camel cased for the API
                "endTime": end_time,
            },
        )

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
                    "curr_candle_spread": round_numbers(curr_candle_spread),
                    "avg_candle_spread": round_numbers(avg_candle_spread),
                    "curr_volume_spread": round_numbers(curr_volume_spread),
                    "avg_volume_spread": round_numbers(avg_volume_spread),
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
