import nose2.tools
import logging
import os
import time

from unittest import mock

from app.log import Log
from app.tz import Tz
from tests.lib.utils import delete_env

TEST_MODULE_NAME = 'TEST_MODULE'
LOG_DIR = 'logs'
LOG_FILE_PATH = f'{LOG_DIR}/{TEST_MODULE_NAME}.log'

mock_basic_config = mock.MagicMock()
mock_handler = mock.MagicMock()
mock_makedirs = mock.MagicMock()


class TestLog:
    @staticmethod
    def setUp() -> None:
        mock_basic_config.reset_mock()
        mock_handler.reset_mock()
        mock_makedirs.reset_mock()

        delete_env('LOGGING_LEVEL')

    @staticmethod
    def tearDown() -> None:
        delete_env('LOGGING_LEVEL')

    @mock.patch('os.makedirs', mock_makedirs)
    @mock.patch('app.log.RotatingFileHandler', mock_handler)
    @mock.patch('logging.basicConfig', mock_basic_config)
    def test_init_logger(self) -> None:
        Log.init_logger(log_name=TEST_MODULE_NAME)

        mock_makedirs.assert_called_once_with('logs', exist_ok=True)

        (_, handler_kwargs) = mock_handler.call_args
        assert handler_kwargs['filename'] == LOG_FILE_PATH

        (_, config_kwargs) = mock_basic_config.call_args
        assert config_kwargs['level'] == logging.INFO

    @mock.patch('os.makedirs', mock_makedirs)
    @mock.patch('app.log.RotatingFileHandler', mock_handler)
    @mock.patch('logging.basicConfig', mock_basic_config)
    @nose2.tools.params(
        ('CRITICAL', logging.CRITICAL),
        ('ERROR', logging.ERROR),
        ('WARNING', logging.WARNING),
        ('INFO', logging.INFO),
        ('DEBUG', logging.DEBUG),
        ('NOTSET', logging.NOTSET),
        ('UNKNOWN', logging.INFO),
    )
    def test_init_logger__env_level(self, logger_level: str, level: int) -> None:
        os.environ['LOGGING_LEVEL'] = logger_level
        Log.init_logger(log_name=TEST_MODULE_NAME)

        (_, config_kwargs) = mock_basic_config.call_args
        assert config_kwargs['level'] == level

    def test_time_converter(self) -> None:
        Log.tz = Tz.timezone()
        converter = Log.time_converter()

        assert type(converter) is time.struct_time
