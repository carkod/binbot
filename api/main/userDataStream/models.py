from flask import current_app as app
from flask import Flask, request
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools, auth
import json
import os
import asyncio
import time
import socket
import requests
from urllib.parse import urlparse
from main.tools import handle_error, set_listenkey, get_listenkey
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



  
  

