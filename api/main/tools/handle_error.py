from flask import current_app as app
from pytz import timezone, UTC
from datetime import timedelta
import time, datetime
import random
import uuid
import requests
import sys
import pandas as pd
import json


def handle_error(req):
	try:
			req.raise_for_status()
			# Binance code errors
			if 'code' in json.loads(req.content).keys():
				code = json.loads(req.content)['code']
				print(json.loads(req.content))
					
	except requests.exceptions.HTTPError as err:
		print(err)