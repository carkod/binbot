from pytz import timezone, UTC
from datetime import timedelta

def nowDatetimeUserTimezone(user_timezone):
	tzone = timezone(user_timezone)
	return datetime.datetime.now(tzone)

def nowDatetimeUTC():
	tzone = UTC
	now = datetime.datetime.now(tzone)
	return now
