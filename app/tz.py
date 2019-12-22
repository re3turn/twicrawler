import logging
import pendulum

from typing import Any

from app.env import Env


class Tz:
    @staticmethod
    def timezone(zone: str = '') -> Any:
        tz_str: str = zone
        if zone == '':
            tz_str = Env.get_environment('TZ')
        if tz_str == '':
            return pendulum.UTC
        else:
            # noinspection PyUnresolvedReferences
            try:
                return pendulum.timezone(tz_str)
            except pendulum.tz.zoneinfo.exceptions.InvalidTimezone:
                return pendulum.UTC


logger: logging.Logger = logging.getLogger(__name__)
