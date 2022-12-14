import pytz
from datetime import datetime


def get_timestamp(tz_name: str = "America/New_York") -> float:
    return datetime.now().astimezone(pytz.timezone(tz_name)).timestamp()
