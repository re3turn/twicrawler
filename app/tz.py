import logging
import pytz

from typing import Any

from app.env import Env


class Tz:
    @staticmethod
    def timezone(zone: str = '') -> Any:
        tz_str: str = zone
        if zone == '':
            tz_str = Env.get_environment('TZ')
        if tz_str == '':
            return pytz.timezone(pytz.utc.zone)
        else:
            try:
                return pytz.timezone(tz_str)
            except pytz.UnknownTimeZoneError:
                return pytz.timezone(pytz.utc.zone)


logger: logging.Logger = logging.getLogger(__name__)
