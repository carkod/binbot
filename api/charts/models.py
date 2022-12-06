from math import ceil
from time import time
from typing import TypedDict

import pandas as pd
from pymongo import ReturnDocument
from api.apis import BinbotApi
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from api.tools.round_numbers import interval_to_millisecs
from flask import current_app, request
from pymongo.errors import DuplicateKeyError
from api.tools.handle_error import InvalidSymbol


class KlinesParams(TypedDict):
    symbol: str
    interval: str
    limit: int


class KlinesSchema:
    def __init__(self, pair, interval=None, limit=300) -> None:
        self._id = pair  # pair
        self.interval = interval
        self.limit = limit
    

    def create(self, data):
        try:
            result = current_app.db.klines.insert_one(
                {"_id": self._id, self.interval: data}
            )
            return result
        except Exception as e:
            return e
    
    def replace_klines(self, data):
        try:
            result = current_app.db.klines.find_one_and_update(
                {"_id": self._id} , {"$set": {self.interval: data}}, upsert=True, return_document=ReturnDocument.AFTER
            )
            return result
        except Exception as e:
            return e

    def update_data(self, data, timestamp=None):
        """
        Function that specifically updates candlesticks.
        Finds existence of candlesticks and then updates with new stream kline data or adds new data
        """
        new_data = data  # This is not existent data but stream data from API
        try:
            kline = current_app.db.klines.find_one({"_id": self._id})
            curr_ts = kline[self.interval][len(kline[self.interval]) - 1][0]
            if curr_ts == timestamp:
                # If found timestamp match - update
                current_app.db.klines.update_one(
                    {"_id": self._id},
                    {"$pop": {self.interval: 1}},
                )
                update_kline = current_app.db.klines.update_one(
                    {"_id": self._id},
                    {"$push": {self.interval: new_data}},
                )
            else:
                # If no timestamp match - push
                update_kline = current_app.db.klines.update_one(
                    {"_id": self._id},
                    {
                        "$push": {
                            self.interval: {
                                "$each": [new_data],
                            }
                        }
                    },
                )

            return update_kline
        except Exception as e:
            return e

    def delete_klines(self):
        result = current_app.db.klines.update_one({"_id": self._id})
        return result


class Candlestick(BinbotApi):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def delete_and_create_klines(self, params):
        """
        Args:
        params

        returns
        df [Pandas dataframe]
        """
        print("Requesting and Cleaning db of incomplete data...")
        data = self.request(url=self.candlestick_url, params=params)
        klines_schema = KlinesSchema(params["symbol"], params["interval"], params["limit"])
        klines = klines_schema.replace_klines(data)
        kline_df = pd.DataFrame(klines[params["interval"]])
        return kline_df

    def check_gaps(self, df, params):
        """
        Checks gaps in the candlestick time series, using the dates difference between dates (index = 0)
        If there are gaps, request data from Binance API (high weight, use cautiously)
        @params
        - df [Pandas dataframe]
        """
        print(f"Checking gaps in the kline data for {params['symbol']}")
        kline_df = df.copy(deep=True)
        df["gaps_check"] = df[0].diff()[1:]
        df = df.dropna()
        if df.empty:
            kline_df = self.delete_and_create_klines(params)
            return kline_df
        gaps_check = df["gaps_check"].to_numpy()

        # Check difference between now and last kline
        try:
            check_latest = ((time() * 1000) - df[0].to_numpy()[-1]) > gaps_check[-1]
        except Exception as e:
            print(e)
        # If true, no gaps
        try:
            no_gaps = gaps_check.all()
            if not bool(no_gaps) or check_latest:
                kline_df = self.delete_and_create_klines(params)
        except IndexError as e:
            print("Check gaps Index Error", e)
            kline_df = self.delete_and_create_klines(params)
        
        return kline_df

    def get_klines(self, binance=False, json=True, params: KlinesParams = None):
        """
        Servers 2 purposes:
        - Endpoint, json=True. @input params as request.args
        - Method returning dataframe and list of dates. @input params arg
        """
        symbol = request.args.get("symbol")
        interval = request.args.get("interval", "15m")
        # 200 limit + 100 Moving Average = 300
        limit = request.args.get("limit", 600)
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

        # Do we require more candlesticks for charts data?
        if params["startTime"]:
            klines = current_app.db.klines.find_one(
                {"_id": params["symbol"], "data.0.0": {"$lte": params["startTime"]}}
            )
        else:
            klines = current_app.db.klines.find_one(
                {"_id": params["symbol"]}
            )

        klines_schema = KlinesSchema(params["symbol"], params["interval"])
        if not klines:
            try:
                if params["startTime"]:
                    # Delete any remnants of this data
                    klines_schema.delete_klines()
                    # Calculate diff start_time and end_time
                    # Divide by interval time to get limit
                    diff_time = (time() * 1000) - int(params["startTime"])
                    # where 15m = 900,000 milliseconds
                    params["limit"] = ceil(
                        diff_time / interval_to_millisecs(params["interval"])
                    )

                # Store more data for db to fill up candlestick charts
                data = self.request(url=self.candlestick_url, params=params)
                if data["code"] == -1121:
                    if json:
                        return jsonResp_error_message(
                            f"Failed to update candlestick data: {data['msg']}"
                        )
                    else:   
                        raise InvalidSymbol()

                klines_schema.replace_klines(data)
                klines = current_app.db.klines.find_one({"_id": params["symbol"]})
            except DuplicateKeyError:
                resp = jsonResp_error_message(f"Duplicate key {params['symbol']}")
                return resp
            except Exception as e:
                return jsonResp_error_message(f"Error creating klines: {e}")

        if not json:
            if klines:
                try:
                    df = pd.DataFrame(klines[params["interval"]])
                    df = self.check_gaps(df, params)
                except Exception as e:
                    print("Error converting to dataframe, deleting and creating new klines", e)
                    df = self.delete_and_create_klines(params)

                dates = df[0].tolist()
            else:
                df = pd.DataFrame([])
                dates = []
            return df, dates

        resp = jsonResp(
            {
                "message": "Successfully retrieved candlesticks",
                "data": str(klines[params["interval"]]),
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
        result = KlinesSchema(pair, interval, limit).update_data(data, stream_data["t"])
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

        Returns: json
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

        params = {
                "limit": limit,
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time,  # starTime and endTime must be camel cased for the API
                "endTime": end_time,
            }

        try:
            df, dates = self.get_klines(
                binance=binance,
                json=False,
                params=params
            )
        except InvalidSymbol:
            return jsonResp_error_message(f"{symbol} doesn't exist")

        if df.empty or len(dates) == 0:
            return jsonResp_error_message(f"There is not enough data for symbol {symbol}")

        trace = self.candlestick_trace(df, dates)
        ma_100, ma_25, ma_7 = self.bollinguer_bands(df, dates)

        if stats:
            high_price = max(df[2])
            low_price = max(df[3])
            amplitude = (float(high_price) / float(low_price)) - 1

            all_time_low = pd.to_numeric(df[3]).min()
            volumes = df[5].tolist()
            resp = jsonResp(
                {
                    "trace": [trace, ma_100, ma_25, ma_7],
                    "interval": interval,
                    "volumes": volumes,
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
