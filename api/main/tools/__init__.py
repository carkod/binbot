from flask import current_app as app
from pytz import timezone, UTC
from datetime import timedelta
import time, datetime
import random
import uuid
import requests

def nowDatetimeUserTimezone(user_timezone):
	tzone = timezone(user_timezone)
	return datetime.datetime.now(tzone)

def nowDatetimeUTC():
	tzone = UTC
	now = datetime.datetime.now(tzone)
	return now

def JsonResp(data, status):
	from flask import Response
	from bson import json_util
	import json
	return Response(json.dumps(data, default=json_util.default), mimetype="application/json", status=status)

def randID():
	randId = uuid.uuid4().hex
	return randId

def randString(length):
	randString = ""
	for _ in range(length):
		randString += random.choice("AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz1234567890")

	return randString

def randStringCaps(length):
	randString = ""
	for _ in range(length):
		randString += random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")

	return randString

def randStringNumbersOnly(length):
	randString = ""
	for _ in range(length):
		randString += random.choice("23456789")

	return randString

def validEmail(email):
	import re

	if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None:
		return True
	else:
		return False


def handle_error(self, req):
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