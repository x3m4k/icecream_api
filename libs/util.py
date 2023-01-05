import pytz
from typing import Optional, Any
from datetime import datetime


class EmptyElement:
    pass


def get_timestamp(tz_name: str = "America/New_York") -> float:
    return datetime.now().astimezone(pytz.timezone(tz_name)).timestamp()


def walk_dict(d, fields: str, default: Optional[Any] = None) -> Any:
    if isinstance(fields, str):
        fields = iter(f for f in fields.split(".") if f)

    try:
        f = next(fields)
    except StopIteration:
        if isinstance(d, type(EmptyElement)):
            return default
        return d

    try:
        obj = d.get(f, EmptyElement)
    except AttributeError:
        if isinstance(d, type(EmptyElement)):
            return default
        return d

    return walk_dict(obj, fields, default=default)
