import os

import requests
from main.tools import (get_listenkey, handle_error, set_listenkey, update_listenkey_timestamp)


class UserDataStream:
    def __init__(self):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_ws_url = os.getenv("WS_BASE")
        self.user_data_stream = os.getenv("USER_DATA_STREAM")
        self.listenkey = None

    def post_user_datastream(self):
        url = self.user_data_stream

        # Get data for a single crypto e.g. BTT in BNB market
        params = []
        headers = {"X-MBX-APIKEY": self.key}

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        set_listenkey(data)
        return data

    def put_user_datastream(self, listenkey):
        """
        Keep alive data stream every 30 min
        Expires every 60 minutes by Binance
        """
        url = self.user_data_stream
        params = [("listenKey", listenkey)]
        headers = {"X-MBX-APIKEY": self.key}

        # Response after request
        res = requests.put(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        update_listenkey_timestamp()
        return data

    def delete_user_datastream(self, listenkey):
        """
        Close user data stream
        """

        url = self.user_data_stream

        params = [("listenKey", listenkey)]
        headers = {"X-MBX-APIKEY": self.key}

        # Response after request
        res = requests.put(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        update_listenkey_timestamp()
        return data
