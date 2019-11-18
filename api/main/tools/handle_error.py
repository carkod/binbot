from flask import current_app as app
from pytz import timezone, UTC
from datetime import timedelta
import time, datetime
import random
import uuid
import requests
import sys
import pandas as pd

def handle_error(req):
	try:
			req.raise_for_status()
	except requests.exceptions.HTTPError as err:
			print(err)
	except requests.exceptions.Timeout:
			# Maybe set up for a retry, or continue in a retry loop
			print('handle_error: Timeout')
	except requests.exceptions.TooManyRedirects:
			# Tell the user their URL was bad and try a different one
			print('handle_error: Too many Redirects')
	except requests.exceptions.RequestException as e:
			# catastrophic error. bail.
			print('handle_error', e)
			sys.exit(1)
	# Binance code errors
 