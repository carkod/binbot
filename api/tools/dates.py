from pytz import timezone, UTC
from datetime import datetime


def nowDatetimeUserTimezone(user_timezone):
    tzone = timezone(user_timezone)
    return datetime.now(tzone)


def nowDatetimeUTC():
    tzone = UTC
    now = datetime.now(tzone)
    return now
