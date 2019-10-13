#!/usr/bin/python3

import psycopg2
import traceback

from datetime import datetime
from typing import Tuple, List, Optional, Any

from app.env import Env
from app.tz import Tz


class Store:
    def __init__(self) -> None:
        self._db_url: str = Env.get_environment('DATABASE_URL', required=True)
        self._sslmode: str = Env.get_environment('DATABASE_SSLMODE', default='require', required=False)
        self._connection: Any = self._get_connection()
        self._tz = Tz.timezone()

    def _get_connection(self) -> Optional[psycopg2.extensions.connection]:
        try:
            connection = psycopg2.connect(self._db_url, sslmode=self._sslmode)
        except Exception as e:
            print(e.args)
            traceback.print_exc()
            return None

        connection.autocommit = True
        return connection

    def insert_tweet_info(self, tweet_id: str, user_id: str, tweet_date: str) -> None:
        add_date: str = datetime.now(self._tz).strftime('%Y-%m-%d %H:%M:%S')
        with self._connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO uploaded_media_tweet (tweet_id, user_id, tweet_date, add_date)'
                'VALUES (%s, %s, %s, %s)',
                (tweet_id, user_id, tweet_date, add_date))

    def insert_failed_upload_media(self, url: str, description: str, user_id: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO failed_upload_media (url, description, user_id)'
                'VALUES (%s, %s, %s)',
                (url, description, user_id))

    def fetch_not_added_tweets(self, tweets: List[str]) -> List[str]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                'SELECT T2.tweet_id '
                'FROM uploaded_media_tweet T1 '
                'RIGHT OUTER JOIN'
                '  (SELECT unnest(%s) as tweet_id) T2 '
                'ON T1.tweet_id = T2.tweet_id '
                'WHERE T1.tweet_id is null',
                (tweets,))
            return cursor.fetchall()

    def fetch_all_failed_upload_medias(self) -> List[Tuple[str, str, str]]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                'SELECT url, description, user_id '
                'FROM failed_upload_media')
            return cursor.fetchall()

    def delete_failed_upload_media(self, url: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                'DELETE FROM failed_upload_media '
                'WHERE url = %s',
                (url,))


if __name__ == '__main__':
    db = Store()
