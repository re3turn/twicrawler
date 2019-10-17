import nose2.tools
import logging
import os

from unittest import mock
from testfixtures import LogCapture

from app.store import Store
from tests.lib.ulit import delete_env

TEST_DATABASE_URL = 'postgres://username:password@hostname:port/database'
TEST_SSLMODE_DEFAULT = 'require'
TEST_TWEET_ID = '1179751757171154944'
TEST_USER_ID = 'test_user'
TEST_DATE = '2020-01-01 00:00:00'
TEST_URL = 'https://pbs.twimg.com/media/test.jpg'
TEST_DESCRIPTION = 'test_description'

mock_get_connection = mock.MagicMock()


@mock.patch('psycopg2.connect', mock_get_connection)
class TestStore:
    def __init__(self) -> None:
        self.clear_env()
        os.environ['DATABASE_URL'] = TEST_DATABASE_URL
        self.store = Store()

    @staticmethod
    def setUp() -> None:
        mock_get_connection.reset_mock(return_value=True, side_effect=True)
        mock_get_connection.cursor.return_value = mock.MagicMock()

    @staticmethod
    def clear_env() -> None:
        delete_env('DATABASE_URL')
        delete_env('DATABASE_SSLMODE')

    def test_get_connection(self) -> None:
        # noinspection PyProtectedMember
        self.store._get_connection()

        mock_get_connection.assert_called_once_with(TEST_DATABASE_URL, sslmode=TEST_SSLMODE_DEFAULT)

    def test_get_connection__exception(self) -> None:
        mock_get_connection.side_effect = Exception()

        with LogCapture(level=logging.ERROR) as log:
            with nose2.tools.such.helper.assertRaises(Exception):
                # noinspection PyProtectedMember
                self.store._get_connection()
            log.check(('app.store', 'ERROR', 'Connection error. exception=()'))

    def test_insert_tweet_info(self) -> None:
        with LogCapture(level=logging.DEBUG) as log:
            self.store.insert_tweet_info(TEST_TWEET_ID, TEST_USER_ID, TEST_DATE)
            log.check(('app.store', 'DEBUG', f'Insert tweet_id={TEST_TWEET_ID}, user_id={TEST_USER_ID}, and '
                                             f'tweet_date={TEST_DATE} into failed_upload_media table.'))

    def test_insert_failed_upload_media(self) -> None:
        with LogCapture(level=logging.DEBUG) as log:
            self.store.insert_failed_upload_media(TEST_URL, TEST_DESCRIPTION, TEST_USER_ID)
            log.check(('app.store', 'DEBUG', f'Insert url={TEST_URL}, description={TEST_DESCRIPTION} and '
                                             f'user_id={TEST_USER_ID} into failed_upload_media table.'))

    def test_fetch_not_added_tweet_ids(self) -> None:
        with LogCapture(level=logging.DEBUG) as log:
            self.store.fetch_not_added_tweet_ids([TEST_TWEET_ID])
            log.check(('app.store', 'DEBUG', 'Fetch not added tweets from uploaded_media_tweet table.'))

    def test_fetch_all_failed_upload_medias(self) -> None:
        with LogCapture(level=logging.DEBUG) as log:
            self.store.fetch_all_failed_upload_medias()
            log.check(('app.store', 'DEBUG', 'Fetch url and description from failed_upload_media table.'))

    def test_delete_failed_upload_media(self) -> None:
        with LogCapture(level=logging.DEBUG) as log:
            self.store.delete_failed_upload_media(TEST_URL)
            log.check(('app.store', 'DEBUG', f'Delete row url={TEST_URL} from failed_upload_media table.'))
