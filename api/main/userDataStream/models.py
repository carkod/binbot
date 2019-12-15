from flask import current_app as app
from flask import Flask, request
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools, auth
import json
import os
import asyncio
import time
from flask_socketio import SocketIO, emit
import requests
from urllib.parse import urlparse
from main.tools import handle_error, set_listenkey, get_listenkey, update_listenkey_timestamp
import hmac
import hashlib
import time as tm

class UserDataStream:

  def __init__(self):
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.base_ws_url = os.getenv("WS_BASE")
    self.user_data_stream = os.getenv("USER_DATA_STREAM")
    self.listenkey = None
  
  
  def post_user_datastream(self):
    url = self.base_url + self.user_data_stream

    # Get data for a single crypto e.g. BTT in BNB market
    params = []
    headers = {'X-MBX-APIKEY': self.key}

    # Response after request
    res = requests.post(url=url, params=params, headers=headers)
    handle_error(res)
    data = res.json()
    set_listenkey(data)
    return data


  """
  Keep alive data stream every 30 min
  Expires every 60 minutes by Binance
  """
  def put_user_datastream(self, listenkey):
    url = self.base_url + self.user_data_stream
    params = [
      ('listenKey', listenkey)
    ]
    headers = {'X-MBX-APIKEY': self.key}

    # Response after request
    res = requests.put(url=url, params=params, headers=headers)
    handle_error(res)
    data = res.json()
    update_listenkey_timestamp()
    return data


  """
  Close user data stream
  """
  def delete_user_datastream(self, listenkey):
    url = self.base_url + self.user_data_stream

    params = [
      ('listenKey', listenkey)
    ]
    headers = {'X-MBX-APIKEY': self.key}

    # Response after request
    res = requests.put(url=url, params=params, headers=headers)
    handle_error(res)
    data = res.json()
    update_listenkey_timestamp()
    return data

  
  def order_update(self):
    emit('my response')

