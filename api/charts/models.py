import logging
from math import ceil
from time import time

import pandas as pd
from pydantic import BaseModel
from pymongo import ReturnDocument

from apis import BinbotApi
from tools.handle_error import (
    InvalidSymbol,
    json_response,
    json_response_error,
    json_response_message
)
from tools.round_numbers import interval_to_millisecs
from db import setup_db
from fastapi.encoders import jsonable_encoder



class CandlestickItemRequest(BaseModel):
    data: list[list]
    symbol: str
    interval: str  # See EnumDefitions
    limit: int = 600
    offset: int = 0


class CandlestickParams(BaseModel):
    symbol: str
    interval: str  # See EnumDefinitions
    limit: int = 600
    startTime: float | None = None  # starTime and endTime must be camel cased for the API
    endTime: float | None = None


class KlinesSchema:
    def __init__(self, pair, interval=None, limit=500) -> None:
        self._id = pair  # pair
        self.interval = interval
        self.limit = limit
        self.db = setup_db()

    def create(self, data):
        try:
            result = self.db.klines.insert_one({"_id": self._id, self.interval: data})
            return result
        except Exception as e:
            return e

    def replace_klines(self, data):
        try:
            result = self.db.klines.find_one_and_update(
                {"_id": self._id},
                {"$set": {self.interval: data}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return result
        except Exception as e:
            return e

    def update_data(self, data, timestamp=None):
        """
        Function that specifically updates candlesticks from websockets
        Finds existence of candlesticks and then updates with new stream kline data or adds new data
        """
        new_data = data  # This is not existent data but stream data from API
        try:
            kline = self.db.klines.find_one({"_id": self._id})
            curr_ts = kline[self.interval][len(kline[self.interval]) - 1][0]
            if curr_ts == timestamp:
                # If found timestamp match - update
                self.db.klines.update_one(
                    {"_id": self._id},
                    {"$pop": {self.interval: 1}},
                )
                update_kline = self.db.klines.update_one(
                    {"_id": self._id},
                    {"$push": {self.interval: new_data}},
                )
            else:
                # If no timestamp match - push
                update_kline = self.db.klines.update_one(
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
        result = self.db.klines.delete_one({"symbol": self._id})
        return result.acknowledged


class Candlestick(BinbotApi):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """
    def __init__(self) -> None:
        self.db = setup_db()

    def delete_and_create_klines(self, params: CandlestickParams):
        """
        Args:
        params

        returns
        df [Pandas dataframe]
        """
        logging.info("Requesting and Cleaning db of incomplete data...")
        if params.limit:
            # Avoid inconsistencies in data
            params.limit = 600

        data = self.request(url=self.candlestick_url, params=vars(params))
        klines_schema = KlinesSchema(params.symbol, params.interval)
        klines = klines_schema.replace_klines(data)
        kline_df = pd.DataFrame(klines[params.interval])
        return kline_df

    def check_gaps(self, df, params: CandlestickParams):
        """
        Checks gaps in the candlestick time series, using the dates difference between dates (index = 0)
        If there are gaps, request data from Binance API (high weight, use cautiously)
        @params
        - df [Pandas dataframe]
        """
        logging.warning(f"Checking gaps in the kline data for {params.symbol}")
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

    def get_klines(self, params):
        """
        Serves parsed klines data from Binance endpoint.
        This function exists to load balance stored data in MongoDB versus polling directly from Binance endpoints.
        If there is up to date data in the MongoDB, it should retrieve it from DB
        If data is not up to date (data contains gaps), it should retrieve from endpoints.


        - params: CandlestickItem. It must provide a symbol at least.
        """

        # Do we require more candlesticks for charts data?
        query = {"_id": params.symbol, params.interval: {"$exists": True}}
        if params.startTime:
            query["data.0.0"] = {"$lte": params.startTime}

        try:
            klines = self.db.klines.find_one(query)
        except Exception as error:
            print(error)
            klines = None
            pass

        if not klines or not isinstance(klines[params.interval], list):
            if params.startTime:
                # Calculate diff start_time and end_time
                # Divide by interval time to get limit
                diff_time = (time() * 1000) - int(params.startTime)
                # where 15m = 900,000 milliseconds
                params.limit = ceil(diff_time / interval_to_millisecs(params.interval))

            # Store more data for db to fill up candlestick charts
            self.delete_and_create_klines(params)
            df, dates = self.get_klines(params)
            return df, dates
        else:
            df = pd.DataFrame(klines[params.interval])
            df = self.check_gaps(df, params)
            dates = df[0].tolist()
        return df, dates
        

    def update_klines(self, item):

        stream_data = item.get("data")
        pair = item.get("symbol")
        interval = item.get("interval")
        limit = item.get("limit", 300)

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
            return json_response_message("Successfully updated candlestick data!")
        else:
            return json_response_error(f"Failed to update candlestick data: {result}")

    def delete_klines(self, symbol: str):
        try:
            KlinesSchema(symbol).delete_klines()
            return json_response_message("Successfully deleted klines")
        except Exception as error:
            return json_response_error(f"Failed deleting klines {symbol}: {error}")

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

    def get(self, symbol, interval="15m", limit=500, start_time: float | None=None, end_time: float | None=None, stats = False):
        """
        Get candlestick graph data
        Index 0: trace
        Index 1: ma_100
        Index 2: ma_25
        Index 3: ma_7
        """

        if not symbol:
            return json_response_error("Symbol is required")
        if not interval:
            return json_response_error("Provide a candlestick interval")

        params = CandlestickParams(
            limit=limit,
            symbol=symbol,
            interval=interval,
            startTime=start_time,  # starTime and endTime must be camel cased for the API
            endTime=end_time,
        )

        try:
            df, dates = self.get_klines(
                params=params,
            )
        except InvalidSymbol:
            return json_response_error(f"{symbol} doesn't exist")
        except Exception as error:
            return json_response_error(f"Error getting klines for {symbol}: {error}")

        if df.empty or len(dates) == 0:
            return json_response_error(f"There is not enough data for symbol {symbol}")

        trace = self.candlestick_trace(df, dates)
        ma_100, ma_25, ma_7 = self.bollinguer_bands(df, dates)

        if stats:
            high_price = max(df[2])
            low_price = max(df[3])
            amplitude = (float(high_price) / float(low_price)) - 1

            all_time_low = pd.to_numeric(df[3]).min()
            volumes = df[5].tolist()

            btc_params = CandlestickParams(
                symbol="BTCUSDT",
                interval="15m",
            )
            btc_df, btc_dates = self.get_klines(btc_params)
            df[1].astype(float)
            open_price_r = df[1].astype(float).corr(btc_df[1].astype(float))
            high_price_r = df[2].astype(float).corr(btc_df[2].astype(float))
            low_price_r = df[3].astype(float).corr(btc_df[3].astype(float))
            close_price_r = df[4].astype(float).corr(btc_df[4].astype(float))
            volume_r = df[5].astype(float).corr(btc_df[5].astype(float))

            close_price_cov = df[4].astype(float).cov(btc_df[4].astype(float))

            # collection of correlations
            p_btc = {
                "open_price": open_price_r,
                "high_price": high_price_r,
                "low_price": low_price_r,
                "close_price": close_price_r,
                "volume": volume_r
            }

            resp = json_response(
                {
                    "trace": [trace, ma_100, ma_25, ma_7],
                    "interval": interval,
                    "volumes": volumes,
                    "amplitude": amplitude,
                    "all_time_low": all_time_low,
                    "btc_correlation": p_btc,
                }
            )
            return resp
        else:
            resp = json_response(
                {"trace": [trace, ma_100, ma_25, ma_7], "interval": interval}, 200
            )
            return resp
