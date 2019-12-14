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
from main.tools import handle_error
import hmac
import hashlib

class UserDataStream():

  def __init__(self):
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("6BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.base_ws_url = os.getenv("WS_BASE")
    self.user_data_stream = os.getenv("USER_DATA_STREAM")
  
  
  def post_user_datastream(self):
    url = self.base_url + self.user_data_stream

    # Get data for a single crypto e.g. BTT in BNB market
    params = []
    headers = {'X-MBX-APIKEY': self.key}

    # Prepare request for signing
    r = requests.Request(url=url, params=params, headers=headers)
    prepped = r.prepare()
    query_string = urlparse(prepped.url).query
    total_params = query_string

    # Generate and append signature
    signature = hmac.new(self.secret.encode(
        'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
    params.append(('signature', signature))

    # Response after request
    res = requests.post(url=url, params=params, headers=headers)
    handle_error(res)
    data = res.json()
    return data
    # @classmethod
    # def recv_frame(self):
    #     frame = super().recv_frame()
    #     print('yay! I got this frame: ', frame)
    #     return frame

# ws = create_connection("ws://echo.websocket.org/", sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),), class_=MyWebSocket)


  
  

