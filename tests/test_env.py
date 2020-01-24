import nose2.tools
import os
import termcolor

from app.env import Env
from tests.lib.utils import delete_env

ENV_VALUE = 'test1234'
DEFAULT_VALUE = 'default_value'
SYS_EXIT = 'sys.exit'
NO_VALUE = ''


class TestEnv:
    @staticmethod
    def setUp() -> None:
        os.environ['_SET_ENV'] = ENV_VALUE

    @staticmethod
    def tearDown() -> None:
        delete_env('_SET_ENV')

    @nose2.tools.params(
        ('_SET_ENV', DEFAULT_VALUE, True, ENV_VALUE),
        ('_SET_ENV', DEFAULT_VALUE, False, ENV_VALUE),
        ('_NO_SET_ENV', DEFAULT_VALUE, False, DEFAULT_VALUE),
        ('_NO_SET_ENV', DEFAULT_VALUE, True, DEFAULT_VALUE)
    )
    def test_get_environment(self, env: str, default: str, required: bool, ans: str) -> None:
        actual = Env.get_environment(env, default, required)
        assert actual == ans

    @nose2.tools.params(
        ('_SET_ENV', ENV_VALUE),
        ('_NO_SET_ENV', NO_VALUE),
    )
    def test_get_environment__env(self, env: str, ans: str) -> None:
        actual = Env.get_environment(env)
        assert actual == ans

    @nose2.tools.params(
        ('_SET_ENV', ENV_VALUE, ENV_VALUE),
        ('_NO_SET_ENV', NO_VALUE, NO_VALUE),
    )
    def test_get_environment__default(self, env: str, default: str, ans: str) -> None:
        actual = Env.get_environment(env, default=default)
        assert actual == ans

    @nose2.tools.params(
        ('_SET_ENV', True, ENV_VALUE),
        ('_SET_ENV', False, ENV_VALUE),
        ('_NO_SET_ENV', True, SYS_EXIT),
        ('_NO_SET_ENV', False, NO_VALUE),
    )
    def test_get_environment__required(self, env: str, required: bool, ans: str) -> None:
        try:
            actual = Env.get_environment(env, required=required)
            assert actual == ans
        except SystemExit as e:
            assert e.code == termcolor.colored(f'Error: Please set environment "{env}"', 'red')
