import nose2.tools
import os
import pendulum

from typing import Optional, Any

from app.tz import Tz
from tests.lib.utils import delete_env


class TestTz:
    @staticmethod
    def setUp() -> None:
        delete_env('TZ')

    @staticmethod
    def tearDown() -> None:
        delete_env('TZ')

    @nose2.tools.params(
        ('Asia/Tokyo', 'Asia/Tokyo'),
        ('', 'UTC'),
        ('unknown', 'UTC'),
        (None, 'UTC'),
    )
    def test_timezone(self, env_timezone: Optional[str], ans: str) -> None:
        if env_timezone:
            os.environ['TZ'] = env_timezone
        timezone = Tz.timezone()
        assert isinstance(timezone, type(pendulum.timezone(ans)))

    @nose2.tools.params(
        ('Asia/Tokyo', 'Asia/Tokyo'),
        ('unknown', 'UTC'),
        ('', 'UTC'),
    )
    def test_timezone__set_param_timezone(self, param_timezone: str, ans: str) -> None:
        timezone: Any = Tz.timezone(param_timezone)
        assert isinstance(timezone, type(pendulum.timezone(ans)))
