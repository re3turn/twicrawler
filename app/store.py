#!/usr/bin/python3

import psycopg2
import os
import pytz
from datetime import datetime


class Store:
    def __init__(self):
        self._db_url = os.environ.get('DATABASE_URL')
        self._sslmode = os.environ.get('DATABASE_SSLMODE', 'require')
        timezone = os.environ.get('TZ')
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
        except:
            import traceback
            traceback.print_exc()
            return None

        connection.autocommit = True
        return connection

    def is_added_tweet(self, tweet_id):
        with self._get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT tweet_id '
                    'FROM uploaded_media_tweet '
                    'WHERE tweet_id = %s',
                    (tweet_id, ))
                tweet_info = cursor.fetchone()
        if tweet_info is None:
            return False

        return True

    def insert_tweet_info(self, tweet_id, user_id, tweet_date):
        add_date = datetime.now(self._tz).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO uploaded_media_tweet (tweet_id, user_id, tweet_date, add_date)'
                    'VALUES (%s, %s, %s, %s)',
                    (tweet_id, user_id, tweet_date, add_date))


if __name__ == '__main__':
    db = Store()
