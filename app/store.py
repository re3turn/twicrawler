#!/usr/bin/python3

import psycopg2
import pytz
import traceback

from datetime import datetime
from app.env import Env


class Store:
    def __init__(self):
        self._db_url = Env.get_environment('DATABASE_URL', required=True)
        self._sslmode = Env.get_environment('DATABASE_SSLMODE', default='require', required=False)
        self._connection = self._get_connection()
        timezone = Env.get_environment('TZ')
        if timezone is None:
            self._tz = pytz.timezone(pytz.utc.zone)
        else:
            try:
                self._tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                self._tz = pytz.timezone(pytz.utc.zone)

    def _get_connection(self):
        try:
            connection = psycopg2.connect(self._db_url, sslmode=self._sslmode)
        except Exception as e:
            print(e.args)
            traceback.print_exc()
            return None

        connection.autocommit = True
        return connection

    def insert_tweet_info(self, tweet_id, user_id, tweet_date):
        add_date = datetime.now(self._tz).strftime('%Y-%m-%d %H:%M:%S')
        with self._connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO uploaded_media_tweet (tweet_id, user_id, tweet_date, add_date)'
                'VALUES (%s, %s, %s, %s)',
                (tweet_id, user_id, tweet_date, add_date))

    def fetch_not_added_tweets(self, tweets: list) -> list:
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


if __name__ == '__main__':
    db = Store()
