import httplib2
import logging
import nose2.tools
import os
import tweepy
import urllib.error

from googleapiclient.errors import HttpError
from testfixtures import LogCapture
from typing import Dict, Tuple, List, Optional
from unittest import mock

from app.crawler import Crawler
from app.google_photos import GooglePhotos
from app.store import Store
from app.twitter import Twitter, TweetMedia, TwitterUser
from tests.test_twitter import TwitterTestUtils
from tests.lib.utils import delete_env, load_json

TEST_TWITTER_ID = 'TwicrawlerT'
TEST_USER_ID = 'test_user_id'
TEST_DESCRIPTION = 'test_description'
TEST_MEDIA_URL = 'https://test.com/test.jpg'
TEST_DOWNLOAD_DIR_PATH = './download/test_user_id'
TEST_TWEET_ID = '1188832511515750404'
TEST_TARGET_ID_COUNT = 1
TEST_MEDIA_TWEETS = 'fav'
TEST_TWEET = 'has_images'
DEFAULT_MODE = 'rt'
DEFAULT_INTERVAL = '5'
JSON_DIR = f'{os.path.dirname(__file__)}/json'

mock_google_photos = mock.MagicMock(GooglePhotos)
mock_twitter = mock.MagicMock(Twitter)
mock_media_tweet = mock.MagicMock(TweetMedia)
mock_store = mock.MagicMock(Store)
mock_request = mock.MagicMock()
mock_makedirs = mock.MagicMock()
mock_rmtree = mock.MagicMock()
mock_sleep = mock.MagicMock()
mock_crawler_func = mock.MagicMock()
mock_crawler_func2 = mock.MagicMock()


@mock.patch('urllib.request', mock_request)
class TestCrawler:
    crawler: Crawler

    @mock.patch('app.crawler.GooglePhotos', mock_google_photos)
    @mock.patch('app.crawler.Twitter', mock_twitter)
    @mock.patch('app.crawler.Store', mock_store)
    @mock.patch('os.makedirs', mock_makedirs)
    def setUp(self) -> None:
        self.clear_env()

        mock_google_photos.reset_mock()
        mock_google_photos.upload_media.reset_mock(side_effect=True)
        mock_twitter.reset_mock(side_effect=True)
        mock_twitter.make_original_image_url.reset_mock(side_effect=True)
        mock_store.reset_mock()
        mock_store.fetch_not_added_tweet_ids.reset_mock(return_value=True)
        mock_store.fetch_all_failed_upload_medias.reset_mock(return_value=True)
        mock_store.insert_tweet_info.reset_mock(side_effect=True)
        mock_store.insert_failed_upload_media.reset_mock(side_effect=True)
        mock_request.reset_mock(side_effect=True)
        mock_request.urlretrieve.reset_mock(side_effect=True)
        mock_makedirs.reset_mock()
        mock_rmtree.reset_mock()
        mock_sleep.reset_mock(side_effect=True)
        mock_crawler_func.reset_mock(side_effect=True, return_value=True)
        mock_crawler_func2.reset_mock(side_effect=True, return_value=True)

        mock_google_photos.return_value = mock_google_photos
        mock_twitter.return_value = mock_twitter
        mock_store.return_value = mock_store

        os.environ['SAVE_MODE'] = 'google'
        self.crawler = Crawler()

    def tearDown(self) -> None:
        self.clear_env()

    @staticmethod
    def clear_env() -> None:
        delete_env('TWITTER_USER_IDS')
        delete_env('INTERVAL')
        delete_env('MODE_SPECIFIED')
        delete_env('TWEET_COUNT')
        delete_env('TWEET_PAGES')
        delete_env('SAVE_MODE')
        delete_env('LOGGING_LEVEL')
        delete_env('DATABASE_URL')
        delete_env('DATABASE_SSLMODE')
        delete_env('TZ')
        delete_env('TWITTER_CONSUMER_KEY')
        delete_env('TWITTER_CONSUMER_SECRET')
        delete_env('TWITTER_ACCESS_TOKEN')
        delete_env('TWITTER_ACCESS_TOKEN_SECRET')
        delete_env('GOOGLE_CLIENT_ID')
        delete_env('GOOGLE_CLIENT_SECRET')
        delete_env('GOOGLE_REFRESH_TOKEN')
        delete_env('GOOGLE_ALBUM_TITLE')

    @staticmethod
    def load_failed_upload_media(json_name: str) -> List[Tuple[str, str]]:
        json_path = f'{JSON_DIR}/crawler/failed_upload_media/{json_name}.json'
        return [tuple(failed_upload_media) for failed_upload_media in load_json(json_path)]  # type: ignore

    @staticmethod
    def load_fetch_all_failed_upload_media(json_name: str) -> List[Tuple[str, str, str]]:
        json_path = f'{JSON_DIR}/crawler/fetch_all_failed_upload_media/{json_name}.json'
        return [tuple(failed_upload_media_info) for failed_upload_media_info in load_json(json_path)]  # type: ignore

    @mock.patch('os.makedirs', mock_makedirs)
    @nose2.tools.params(
        ('https://test.com/test.jpg', 'download_dir/path/test.jpg'),
    )
    def test_download_media(self, media_url: str, download_path: str) -> None:
        mock_makedirs.reset_mock()
        self.crawler.download_media(media_url, download_path)

        mock_makedirs.assert_called_once_with(os.path.dirname(download_path), exist_ok=True)
        mock_request.urlretrieve.assert_called_once_with(media_url, download_path)

    @nose2.tools.params(
        ('download_dir/path/test.jpg', 'test description', True),
    )
    def test_upload_google_photos(self, media_path: str, description: str, ans: bool) -> None:
        is_upload: bool = self.crawler.upload_google_photos(media_path, description)
        assert is_upload is ans
        mock_google_photos.upload_media.assert_called_once_with(media_path, description)

    @nose2.tools.params(
        (500, 'Server Error'),
    )
    def test_upload_google_photos__http_error(self, status: int, reason: str) -> None:
        res: dict = {'status': status, 'reason': reason}
        error_response = httplib2.Response(res)
        error_response.reason = reason
        mock_google_photos.upload_media.side_effect = HttpError(resp=error_response, content=b"{}")

        with LogCapture() as log:
            is_upload: bool = self.crawler.upload_google_photos('media_path', 'description')
            msg = f'HTTP status={reason}'
            log.check(('app.crawler', 'ERROR', msg))
        assert is_upload is False

    @nose2.tools.params(
        'Any exception'
    )
    def test_upload_google_photos__any_exception(self, reason: str) -> None:
        mock_google_photos.upload_media.side_effect = Exception(reason)
        self.crawler.google_photos = mock_google_photos

        with LogCapture() as log:
            is_upload: bool = self.crawler.upload_google_photos('media_path', 'description')
            msg = f'Error reason={reason}'
            log.check(('app.crawler', 'ERROR', msg))
        assert is_upload is False
        mock_google_photos.upload_media.reset_mock(side_effect=True)

    @nose2.tools.params(
        ('https://test.com/test.jpg', 'test_user', 'test_user/test.jpg')
    )
    def test_make_download_path(self, url: str, user_id: str, ans: str) -> None:
        download_path: str = self.crawler.make_download_path(url, user_id)
        # noinspection PyProtectedMember
        assert download_path == f'{self.crawler._download_dir}/{ans}'

    @mock.patch('shutil.rmtree', mock_rmtree)
    @mock.patch('os.makedirs', mock_makedirs)
    @nose2.tools.params(
        ('https://test.com/test.jpg', 'other', 'google'),
        ('https://pbs.twimg.com/media/test.png', 'Twitter', 'google'),
        ('http://pbs.twimg.com/media/test.jpg', 'Twitter', 'local')
    )
    def test_save_media(self, url: str, media_type: str, save_mode: str) -> None:
        self.crawler._save_mode = save_mode
        mock_twitter.make_original_image_url.side_effect = Twitter.make_original_image_url

        # make log msg
        msg_url = url
        if media_type == 'Twitter':
            msg_url = f'{url}?name=orig'
        download_path = f'{TEST_DOWNLOAD_DIR_PATH}/{os.path.basename(url)}'
        download_file_msg = f'Download file. url={msg_url}, path={download_path}'
        delete_msg = f'Delete directory. path={TEST_DOWNLOAD_DIR_PATH}'

        with LogCapture() as log:
            is_save = self.crawler.save_media(url, TEST_DESCRIPTION, TEST_USER_ID)
            if save_mode == 'local':
                log.check(('app.crawler', 'DEBUG', download_file_msg))
            elif save_mode == 'google':
                log.check(('app.crawler', 'DEBUG', download_file_msg), ('app.crawler', 'DEBUG', delete_msg))
        assert is_save is True

        if save_mode == 'local':
            assert mock_google_photos.upload_media.call_count == 0
        elif save_mode == 'google':
            assert mock_google_photos.upload_media.call_count == 1

    @mock.patch('time.sleep', mock_sleep)  # for retry
    def test_save_media__download_failed(self) -> None:
        mock_request.urlretrieve.side_effect = urllib.error.HTTPError(TEST_MEDIA_URL, code='500', msg='', hdrs='',
                                                                      fp=None)

        with LogCapture(level=logging.ERROR) as log:
            is_save = self.crawler.save_media(TEST_MEDIA_URL, TEST_DESCRIPTION, TEST_USER_ID)
            log.check(('app.crawler', 'ERROR', f'Download failed. media_url={TEST_MEDIA_URL}'))
        assert is_save is False

    @mock.patch('time.sleep', mock_sleep)  # for retry
    def test_save_media__upload_failed(self) -> None:
        mock_google_photos.upload_media.side_effect = Exception()

        with LogCapture(level=logging.ERROR) as log:
            is_save = self.crawler.save_media(TEST_MEDIA_URL, TEST_DESCRIPTION, TEST_USER_ID)
            log.check(('app.crawler', 'ERROR', 'Error reason='),
                      ('app.crawler', 'ERROR', f'upload failed. media_url={TEST_MEDIA_URL}'))
        assert is_save is False

    @mock.patch('tests.test_twitter.TweetMedia', mock_media_tweet)
    @mock.patch('app.crawler.Crawler.store_tweet_info', mock_crawler_func)
    @nose2.tools.params(
        'local',
        'google'
    )
    def test_backup_media(self, save_mode: str) -> None:
        mock_store.fetch_not_added_tweet_ids.return_value = [(TEST_TWEET_ID,)]
        self.crawler._save_mode = save_mode
        target_media_tweets: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(TEST_MEDIA_TWEETS)
        target_media_tweet = target_media_tweets[TEST_TWEET_ID]

        with LogCapture(level=logging.DEBUG) as log:
            self.crawler.backup_media(target_media_tweets)
            log.check(('app.crawler', 'INFO', f'Target tweet media count={TEST_TARGET_ID_COUNT}'),
                      ('app.crawler', 'DEBUG', f'All media upload succeeded. urls={target_media_tweet.urls}'))

            mock_crawler_func.assert_called_once_with(target_media_tweets[TEST_TWEET_ID].tweet)

        if save_mode == 'local':
            assert mock_google_photos.init_album.call_count == 0
        elif save_mode == 'google':
            assert mock_google_photos.init_album.call_count == 1

    def test_backup_media__no_new_tweet(self) -> None:
        with LogCapture(level=logging.INFO) as log:
            self.crawler.backup_media({})
            log.check(('app.crawler', 'INFO', 'No new tweet media.'))

    def test_backup_media__no_new_tweet_ids(self) -> None:
        mock_store.fetch_not_added_tweet_ids.return_value = []
        target_media_tweets: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(TEST_MEDIA_TWEETS)

        with LogCapture(level=logging.INFO) as log:
            self.crawler.backup_media(target_media_tweets)
            log.check(('app.crawler', 'INFO', 'No new tweet media.'))

    @mock.patch('app.crawler.Crawler.store_failed_upload_media', mock_crawler_func)
    def test_backup_media__save_failed(self) -> None:
        mock_store.fetch_not_added_tweet_ids.return_value = [(TEST_TWEET_ID,)]
        target_media_tweets: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(TEST_MEDIA_TWEETS)
        target_media_tweet = target_media_tweets[TEST_TWEET_ID]
        url = target_media_tweet.urls[0]

        with mock.patch('app.crawler.Crawler.save_media', return_value=False):
            with LogCapture(level=logging.WARNING) as log:
                self.crawler.backup_media(target_media_tweets)
                log.check(('app.crawler', 'WARNING', f'Save failed. tweet_id={TEST_TWEET_ID}, media_url={url}'))

        target_tweet: tweepy.Status = target_media_tweets[TEST_TWEET_ID].tweet
        failed_upload_media: List[Tuple[str, str]] = self.load_failed_upload_media('one')
        mock_crawler_func.assert_called_once_with(target_tweet, failed_upload_media)

    def test_store_tweet_info(self) -> None:
        target_tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=TEST_TWEET)
        self.crawler.store_tweet_info(target_tweet)
        mock_store.insert_tweet_info.assert_called_once_with(target_tweet.id_str, target_tweet.user.screen_name,
                                                             str(target_tweet.created_at))

    def test_store_tweet_info__exception(self) -> None:
        mock_store.insert_tweet_info.side_effect = Exception()

        target_tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=TEST_TWEET)
        with LogCapture(level=logging.ERROR) as log:
            self.crawler.store_tweet_info(target_tweet)
            log.check(('app.crawler', 'ERROR', f'Insert failed. tweet_id={target_tweet.id_str}, exception=()'))

    def test_store_failed_upload_media(self) -> None:
        target_tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name='has_video')
        failed_upload_media: List[Tuple[str, str]] = self.load_failed_upload_media('one')

        self.crawler.store_failed_upload_media(target_tweet, failed_upload_media)
        failed_url, description = failed_upload_media[0]
        mock_store.insert_failed_upload_media.assert_called_once_with(failed_url, description,
                                                                      target_tweet.user.screen_name)

    def test_store_failed_upload_media__three(self) -> None:
        target_tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name='has_instagram_url')
        failed_upload_media: List[Tuple[str, str]] = self.load_failed_upload_media('three')

        self.crawler.store_failed_upload_media(target_tweet, failed_upload_media)
        assert mock_store.insert_failed_upload_media.call_count == 3

    def test_store_failed_upload_media__exception(self) -> None:
        mock_store.insert_failed_upload_media.side_effect = Exception()
        target_tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name='has_video')
        failed_upload_media: List[Tuple[str, str]] = self.load_failed_upload_media('one')
        failed_url, description = failed_upload_media[0]

        with LogCapture(level=logging.ERROR) as log:
            self.crawler.store_failed_upload_media(target_tweet, failed_upload_media)
            log.check(('app.crawler', 'ERROR', f'Insert failed. failed_url={failed_url}, description={description},'
                                               f' exception=()'))

    @mock.patch('app.crawler.Crawler.save_media', mock_crawler_func)
    def test_retry_backup_media(self) -> None:
        all_failed_upload_media: List[Tuple[str, str, str]] = self.load_fetch_all_failed_upload_media('one')
        mock_store.fetch_all_failed_upload_medias.return_value = all_failed_upload_media
        url, description, user_id = all_failed_upload_media[0]

        with LogCapture(level=logging.INFO) as log:
            self.crawler.retry_backup_media()
            log.check(('app.crawler', 'INFO', f'Retry Save media. media_url={url}'))

        mock_store.fetch_all_failed_upload_medias.assert_called_once_with()
        mock_store.delete_failed_upload_media.assert_called_once_with(url)
        mock_crawler_func.assert_called_once_with(url, description, user_id)

    @mock.patch('app.crawler.Crawler.save_media', mock_crawler_func)
    def test_retry_backup_media__three(self) -> None:
        all_failed_upload_media: List[Tuple[str, str, str]] = self.load_fetch_all_failed_upload_media('three')
        mock_store.fetch_all_failed_upload_medias.return_value = all_failed_upload_media

        self.crawler.retry_backup_media()
        assert mock_crawler_func.call_count == 3

    def test_retry_backup_media__save_failed(self) -> None:
        all_failed_upload_media: List[Tuple[str, str, str]] = self.load_fetch_all_failed_upload_media('one')
        mock_store.fetch_all_failed_upload_medias.return_value = all_failed_upload_media
        url, _, _ = all_failed_upload_media[0]

        with mock.patch('app.crawler.Crawler.save_media', return_value=False):
            with LogCapture(level=logging.WARNING) as log:
                self.crawler.retry_backup_media()
                log.check(('app.crawler', 'WARNING', f'Retry Save failed. media_url={url}'))

        mock_store.delete_failed_upload_media.assert_not_called()

    @mock.patch('app.crawler.Crawler.save_media', mock_crawler_func)
    def test_retry_backup_media__exception(self) -> None:
        mock_crawler_func.side_effect = Exception()
        all_failed_upload_media: List[Tuple[str, str, str]] = self.load_fetch_all_failed_upload_media('one')
        mock_store.fetch_all_failed_upload_medias.return_value = all_failed_upload_media
        url, _, _ = all_failed_upload_media[0]

        with LogCapture(level=logging.ERROR) as log:
            self.crawler.retry_backup_media()
            log.check(('app.crawler', 'ERROR', f'Retry backup failed. failed_url={url}, exception=()'))

    @mock.patch('app.crawler.Crawler.backup_media', mock_crawler_func)
    @mock.patch('app.crawler.Crawler.retry_backup_media', mock_crawler_func2)
    def test_crawling_tweets(self) -> None:
        mock_twitter.get_target_tweets.return_value = {}
        user = TwitterUser(id=TEST_TWITTER_ID)
        self.crawler.crawling_tweets(user)

        mock_twitter.get_target_tweets(user)
        mock_crawler_func.assert_called_once_with({})
        mock_crawler_func2.assert_called_once_with()

    @mock.patch('time.sleep', mock_sleep)
    @mock.patch('app.crawler.Crawler.crawling_tweets', mock_crawler_func)
    @nose2.tools.params(
        '10',
        None
    )
    def test_main(self, interval: Optional[str]) -> None:
        mock_sleep.side_effect = Exception()
        setattr(mock_twitter, 'mode', DEFAULT_MODE)

        test_interval: str = DEFAULT_INTERVAL
        if interval:
            os.environ['INTERVAL'] = interval
            test_interval = interval
        os.environ['TWITTER_USER_IDS'] = TEST_TWITTER_ID

        with LogCapture(level=logging.INFO) as log:
            with nose2.tools.such.helper.assertRaises(Exception):
                self.crawler.main()
            log.check(('app.crawler', 'INFO', f'Crawling start. user = {TEST_TWITTER_ID}, mode={DEFAULT_MODE}'),
                      ('app.crawler', 'INFO', f'Interval. sleep {test_interval} minutes.'))

        mock_crawler_func.assert_called_once_with(TwitterUser(id=TEST_TWITTER_ID))

    @mock.patch('time.sleep', mock_sleep)
    @mock.patch('app.crawler.Crawler.crawling_tweets', mock_crawler_func)
    def test_main__exception(self) -> None:
        mock_sleep.side_effect = Exception()
        mock_crawler_func.side_effect = Exception()
        setattr(mock_twitter, 'mode', DEFAULT_MODE)
        os.environ['TWITTER_USER_IDS'] = TEST_TWITTER_ID

        with LogCapture(level=logging.ERROR) as log:
            with nose2.tools.such.helper.assertRaises(Exception):
                self.crawler.main()
            log.check(('app.crawler', 'ERROR', 'Crawling error exception=()'))
