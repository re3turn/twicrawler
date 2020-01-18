import logging
import os

from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.env import Env
from app.tz import Tz


class Log:
    tz: Any
    format: str = '[%(asctime)s] %(module)s.%(funcName)s %(levelname)s: %(message)s'

    @classmethod
    def init_logger(cls, log_name: str) -> None:
        level: int = logging.INFO
        logger_level: str = Env.get_environment('LOGGING_LEVEL', default='INFO')
        if type(logging.getLevelName(logger_level)) is int:
            level = logging.getLevelName(logger_level)

        os.makedirs('logs', exist_ok=True)

        cls.tz = Tz.timezone()
        logging.Formatter.converter = cls.time_converter

        stream_handler = logging.StreamHandler()

        file_handler = RotatingFileHandler(
            filename=f'logs/{log_name}.log',
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )

        # noinspection PyArgumentList
        logging.basicConfig(
            handlers=[stream_handler, file_handler],
            format=cls.format,
            level=level,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger('googleapiclient').setLevel(logging.WARNING)
        logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING)

    @classmethod
    def time_converter(cls, *args: Any) -> Any:
        _ = args
        return datetime.now(cls.tz).timetuple()
