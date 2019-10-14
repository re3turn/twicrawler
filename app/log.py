import logging

from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict

from app.env import Env
from app.tz import Tz


class Log:
    tz: Any
    format: str = '[%(asctime)s] %(module)s.%(funcName)s %(levelname)s: %(message)s'
    level_dict: Dict[str, int] = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING,
                                  'INFO': logging.INFO, 'DEBUG': logging.DEBUG, 'NOTSET': logging.NOTSET}

    @classmethod
    def init_logger(cls,  log_name: str, level: int = logging.INFO) -> None:
        logger_level: str = Env.get_environment('LOGGER_LEVEL', default='INFO')
        if logger_level != 'INFO' and logger_level in cls.level_dict:
            level = cls.level_dict[logger_level]

        cls.tz = Tz.timezone()
        logging.Formatter.converter = cls.time_converter

        stream_handler = logging.StreamHandler()

        file_handler = RotatingFileHandler(
            filename=f'logs/{log_name}.log',
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )

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
        return datetime.now(cls.tz).timetuple()

