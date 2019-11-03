#!/usr/bin/python3

import logging
import psycopg2

from datetime import datetime
from typing import Tuple, List, Optional, Any

from app.env import Env
from app.log import Log
from app.tz import Tz

MAX_CONNECTION_RETRY = 3


class Store:
    def __init__(self) -> None:
        self._db_url: str = Env.get_environment('DATABASE_URL', required=True)
        self._sslmode: str = Env.get_environment('DATABASE_SSLMODE', default='require', required=False)
        self._connection: Any = self._get_connection()
        self._tz = Tz.timezone()

        logger.debug(f'Store setting info. _db_url={self._db_url}, _sslmode={self._sslmode}')

    def _get_connection(self) -> Optional[psycopg2.extensions.connection]:
        try:
            connection = psycopg2.connect(self._db_url, sslmode=self._sslmode)
        except Exception as e:
            logger.exception(f'Connection error. exception={e.args}')
            return None

        connection.autocommit = True
        return connection

    def _execute_query(self, query: str,
                       variables: Optional[Tuple[Any, ...]] = None) -> Optional[List[Tuple[Any, ...]]]:
        for i in range(MAX_CONNECTION_RETRY + 1):
            try:
                with self._connection.cursor() as cursor:
                    cursor.execute(query, variables)
                    return cursor.fetchall()
            except psycopg2.InterfaceError as e:
                if i == MAX_CONNECTION_RETRY:
                    raise e
                logger.warning(f'Reconnection. exception={e.args}')
                self._connection = self._get_connection()
            except psycopg2.ProgrammingError:
                #  Not produce any result set
                return None

    def insert_tweet_info(self, tweet_id: str, user_id: str, tweet_date: str) -> None:
        logger.debug(f'Insert tweet_id={tweet_id}, user_id={user_id}, and tweet_date={tweet_date} '
                     f'into failed_upload_media table.')
        add_date: str = datetime.now(self._tz).strftime('%Y-%m-%d %H:%M:%S')
        query: str = 'INSERT INTO uploaded_media_tweet (tweet_id, user_id, tweet_date, add_date) ' \
                     'VALUES (%s, %s, %s, %s)'
        self._execute_query(query=query, variables=(tweet_id, user_id, tweet_date, add_date))

    def insert_failed_upload_media(self, url: str, description: str, user_id: str) -> None:
        logger.debug(f'Insert url={url}, description={description} and user_id={user_id} '
                     f'into failed_upload_media table.')
        with self._connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO failed_upload_media (url, description, user_id)'
                'VALUES (%s, %s, %s)',
                (url, description, user_id))

    def fetch_not_added_tweets(self, tweets: List[str]) -> List[Tuple[str]]:
        logger.debug('Fetch not added tweets from uploaded_media_tweet table.')
        query: str = 'SELECT T2.tweet_id ' \
                     'FROM uploaded_media_tweet T1 ' \
                     'RIGHT OUTER JOIN' \
                     '  (SELECT unnest(%s) as tweet_id) T2 ' \
                     'ON T1.tweet_id = T2.tweet_id ' \
                     'WHERE T1.tweet_id is null'
        return self._execute_query(query=query, variables=(tweets,))

    def fetch_all_failed_upload_medias(self) -> List[Tuple[str, str, str]]:
        logger.debug('Fetch url and description from failed_upload_media table.')
        query: str = 'SELECT url, description, user_id ' \
                     'FROM failed_upload_media'
        return self._execute_query(query=query)

    def delete_failed_upload_media(self, url: str) -> None:
        logger.debug(f'Delete row url={url} from failed_upload_media table.')
        query: str = 'DELETE FROM failed_upload_media ' \
                     'WHERE url = %s'
        self._execute_query(query=query, variables=(url,))


if __name__ == '__main__':
    Log.init_logger(log_name='store')
    logger: logging.Logger = logging.getLogger(__name__)
    db = Store()

logger = logging.getLogger(__name__)
