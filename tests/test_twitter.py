import nose2.tools
import logging
import os
import re
import tweepy

from testfixtures import LogCapture
from typing import Iterator, Dict, List, Optional
from tweepy.models import ResultSet
from unittest import mock

from app.instagram import Instagram
from app.twitter import Twitter, TwitterUser, TweetMedia
from app.util import has_attributes
from tests.lib.logcapture_helper import LogCaptureHelper
from tests.lib.utils import load_json, delete_env

TEST_TWITTER_ID: str = 'TwicrawlerT'
JSON_DIR = f'{os.path.dirname(__file__)}/json'
INSTAGRAM_DUMMY_URL = 'https://scontent-nrt1-1.cdninstagram.com/vp/test.jpg'

mock_instagram = mock.MagicMock(Instagram)
mock_cursor = mock.MagicMock(tweepy.Cursor)
mock_twitter_func = mock.MagicMock()


class MockTweepyCursor:
    @classmethod
    def pages(cls, _: int) -> Iterator[ResultSet]:
        json_name = 'timeline'
        (_, kwargs) = mock_cursor.call_args
        if 'since_id' not in kwargs:
            json_name = 'fav'
        json_path = f'{JSON_DIR}/twitter/tweets/{json_name}.json'
        tweets: list = load_json(json_path)

        tweet_list: ResultSet = ResultSet(max_id=1, since_id=1)

        for tweet_dict in tweets:
            tweet_list.append(tweepy.Status.parse(tweepy.api, tweet_dict))
        return iter([tweet_list])


class TwitterTestUtils:
    @staticmethod
    def load_target_media_tweets(json_name: str) -> Dict[str, TweetMedia]:
        json_path = f'{JSON_DIR}/twitter/target_tweet_medias/{json_name}.json'
        target_tweet_medias: dict = load_json(json_path)

        return {tweet_id: TweetMedia(urls=media_info['urls'],
                                     tweet=tweepy.Status.parse(tweepy.api, media_info['tweet']))
                for tweet_id, media_info in target_tweet_medias.items()}

    @staticmethod
    def load_tweet(json_name: str) -> tweepy.Status:
        json_path = f'{JSON_DIR}/twitter/tweet/{json_name}.json'
        return tweepy.Status.parse(tweepy.api, load_json(json_path))


class TestTweetMedia:
    @nose2.tools.params(
        'fav'
    )
    def test_show_info(self, json_name: str) -> None:
        target_tweet_medias: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(json_name=json_name)
        for _, tweet_media in target_tweet_medias.items():
            urls: List[str] = tweet_media.urls
            tweet: tweepy.Status = tweet_media.tweet
            msg = f'user_id={tweet.user.screen_name}, tweet_date={str(tweet.created_at)}, ' \
                  f'permalink={Twitter.make_tweet_permalink(tweet)}, media_urls={urls}'
            with LogCapture() as log:
                tweet_media.show_info()
                log.check(('app.twitter', 'INFO', msg))


@mock.patch('tweepy.Cursor', mock_cursor)
@mock.patch('app.twitter.Instagram', mock_instagram)
class TestTwitter:
    twitter: Twitter
    mock_cursor: mock.MagicMock
    mock_instagram: mock.MagicMock

    def __init__(self) -> None:
        self.user: TwitterUser = TwitterUser(id=TEST_TWITTER_ID)

    def setUp(self) -> None:
        os.environ['TWITTER_CONSUMER_KEY'] = 'DUMMY'
        os.environ['TWITTER_CONSUMER_SECRET'] = 'DUMMY'
        os.environ['TWITTER_ACCESS_TOKEN'] = 'DUMMY'
        os.environ['TWITTER_ACCESS_TOKEN_SECRET'] = 'DUMMY'

        self.mock_cursor = mock.MagicMock(tweepy.Cursor)
        self.mock_instagram = mock.MagicMock(Instagram)

        mock_cursor.reset_mock()
        mock_cursor.pages.reset_mock(side_effect=True)
        mock_instagram.reset_mock()
        mock_twitter_func.reset_mock()

        # Return mock when instantiating
        mock_cursor.return_value = self.mock_cursor
        mock_instagram.return_value = self.mock_instagram

        self.twitter = Twitter()

    @staticmethod
    def tearDown() -> None:
        delete_env('TWITTER_CONSUMER_KEY')
        delete_env('TWITTER_CONSUMER_SECRET')
        delete_env('TWITTER_ACCESS_TOKEN')
        delete_env('TWITTER_ACCESS_TOKEN_SECRET')

    @nose2.tools.params(
        ('test.jpg', 'test.jpg?name=orig'),
        ('test.jpg?foo=bar', 'test.jpg?foo=bar&name=orig'),
        ('test.jpg?name=100', 'test.jpg?name=orig'),
        ('test.jpg?name=aBc789', 'test.jpg?name=orig'),
        ('test.jpg?name=aBc789&foo=aaa', 'test.jpg?name=orig&foo=aaa')
    )
    def test_make_original_image_url(self, url: str, ans: str) -> None:
        original_url: str = Twitter.make_original_image_url(url)
        assert original_url == ans

    @nose2.tools.params(
        ('is_fav_rt_quoted', True),
        ('is_not_fav_rt_quoted', False)
        # Maybe quoted_status never be empty
    )
    def test_is_quoted(self, json_name: str, ans: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        result: bool = Twitter.is_quoted(tweet)
        assert result is ans

    @nose2.tools.params(
        ('is_fav_rt_quoted', True),
        ('is_not_fav_rt_quoted', False)
        # Maybe favorited is always included
    )
    def test_is_favorited(self, json_name: str, ans: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        result: bool = Twitter.is_favorited(tweet)
        assert result is ans

    @nose2.tools.params(
        ('is_fav_rt_quoted', True),
        ('is_not_fav_rt_quoted', False)
        # Maybe retweeted_status never be empty
    )
    def test_is_retweeted(self, json_name: str, ans: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        result: bool = Twitter.is_retweeted(tweet)
        assert result is ans

    @nose2.tools.params(
        ('has_images', True),
        ('has_illegal_images', False)
        # Maybe media_url_https is always included
    )
    def test_get_photo_url(self, json_name: str, has_url: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        assert has_attributes(tweet, 'extended_entities') and 'media' in tweet.extended_entities
        pattern = re.compile(r'^https?://([\w-]+\.)+[\w-]+/?([\w\-./?%&=+]*)?$')
        for media in tweet.extended_entities['media']:
            # noinspection PyProtectedMember
            url: str = Twitter._get_photo_url(media)
            if has_url:
                assert pattern.fullmatch(url) is not None
            else:
                assert len(url) == 0

    @nose2.tools.params(
        ('has_video', True),
        ('has_illegal_video', False)
    )
    def test_get_video_url(self, json_name: str, has_url: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        assert has_attributes(tweet, 'extended_entities') and 'media' in tweet.extended_entities
        pattern = re.compile(r'^https?://([\w-]+\.)+[\w-]+/?([\w\-./?%&=+]*)?$')
        for media in tweet.extended_entities['media']:
            # noinspection PyProtectedMember
            url: str = Twitter._get_video_url(media)
            if has_url:
                assert pattern.fullmatch(url) is not None
            else:
                assert len(url) == 0

    @nose2.tools.params(
        ('has_instagram_url', True),
        ('has_not_images', False)
        # Maybe urls never be empty
    )
    def test_has_instagram_url(self, json_name: str, has_url: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        assert has_attributes(tweet, 'entities')
        # noinspection PyProtectedMember
        assert Twitter._has_instagram_url(tweet.entities) is has_url

    @nose2.tools.params(
        ('has_images', False),
        ('has_instagram_url', True),
        ('has_illegal_instagram_url', True)
    )
    def test_get_instagram_url(self, json_name: str, has_url: bool) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        assert has_attributes(tweet, 'entities')
        # noinspection PyProtectedMember
        url: str = Twitter._get_instagram_url(tweet.entities)
        assert isinstance(url, str)
        if has_url:
            pattern = re.compile(r'^https?://([\w-]+\.)+[\w-]+/?([\w\-./?%&=+]*)?$')
            assert pattern.fullmatch(url) is not None
        else:
            assert len(url) == 0

    @nose2.tools.params(
        'has_images',
        'has_video'
        # Maybe extended_entities never be empty
    )
    def test_get_twitter_media_urls(self, json_name: str) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        assert has_attributes(tweet, 'extended_entities')
        # noinspection PyProtectedMember
        media_url_list: List[str] = self.twitter._get_twitter_media_urls(tweet.extended_entities)

        assert len(media_url_list) != 0
        pattern = re.compile(r'^https?://([\w-]+\.)+[\w-]+/?([\w\-./?%&=+]*)?$')
        for url in media_url_list:
            assert pattern.fullmatch(url) is not None

    @nose2.tools.params(
        ('has_images', 'Twitter'),
        ('has_not_images', None),
        ('has_instagram_url', 'Instagram')
    )
    def test_get_tweet_medias(self, json_name: str, media_type: Optional[str]) -> None:
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name=json_name)
        target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_tweet_medias(tweet)

        if media_type is None:
            assert len(target_tweet_medias) == 0
            return
        for key, value in target_tweet_medias.items():
            assert isinstance(key, str)
            assert isinstance(value, TweetMedia)
            assert len(value.urls) != 0

    def test_make_tweet_permalink(self) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name='has_images')
        permalink: str = self.twitter.make_tweet_permalink(tweet)
        assert f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}' == permalink

    def test_make_tweet_description(self) -> None:
        tweet: tweepy.Status = TwitterTestUtils.load_tweet(json_name='has_images')
        description: str = self.twitter.make_tweet_description(tweet)
        assert f'{tweet.user.name}\n' \
               f'@{tweet.user.screen_name}\n' \
               f'{tweet.full_text}' == description

    def test_difference_tweet_medias(self) -> None:
        old_tweets: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(json_name='old')
        new_tweets: Dict[str, TweetMedia] = TwitterTestUtils.load_target_media_tweets(json_name='new')
        target_tweet_medias: Dict[str, TweetMedia] = Twitter.difference_tweet_medias(new_tweets, old_tweets)

        assert len(target_tweet_medias) == 1

    @nose2.tools.params(
        6,
    )
    def test_get_favorite_media(self, count: int) -> None:
        self.mock_cursor.pages.side_effect = MockTweepyCursor.pages
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]

        with LogCapture(level=logging.INFO) as log:
            target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_favorite_media(self.user)
            log.check(('app.twitter', 'INFO', f'Get favorite tweet media. user={self.user.id}. '
                                              f'pages={self.twitter.tweet_page}, count={self.twitter.tweet_count}'))

        assert len(target_tweet_medias) == count
        for tweet_id, tweet_media in target_tweet_medias.items():
            assert isinstance(tweet_id, str)
            assert isinstance(tweet_media, TweetMedia)

    @mock.patch('app.crawler.Twitter.get_tweet_medias', mock_twitter_func)
    def test_get_favorite_media__exception(self) -> None:
        self.mock_cursor.pages.side_effect = MockTweepyCursor.pages
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]

        mock_twitter_func.side_effect = Exception()

        with LogCapture(level=logging.ERROR) as log:
            target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_favorite_media(self.user)
            assert LogCaptureHelper.check_contain(log, ('app.twitter', 'ERROR', 'Get tweet media error. exception=()'))

        assert len(target_tweet_medias) == 0

    @nose2.tools.params(
        ('rt', 7),
        ('rtfav', 7),
        ('rrrt', 7),
        ('mixed', 3),
    )
    def test_get_rt_media(self, mode: str, count: int) -> None:
        self.mock_cursor.pages.side_effect = MockTweepyCursor.pages
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]
        self.twitter.mode = mode
        target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_rt_media(self.user)

        assert len(target_tweet_medias) == count
        for tweet_id, tweet_media in target_tweet_medias.items():
            assert isinstance(tweet_id, str)
            assert isinstance(tweet_media, TweetMedia)

    @mock.patch('app.crawler.Twitter.get_tweet_medias', mock_twitter_func)
    def test_get_rt_media__exception(self) -> None:
        self.mock_cursor.pages.side_effect = MockTweepyCursor.pages
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]

        mock_twitter_func.side_effect = Exception()

        with LogCapture(level=logging.ERROR) as log:
            target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_rt_media(self.user)
            assert LogCaptureHelper.check_contain(log, ('app.twitter', 'ERROR', 'Get tweet media error. exception=()'))

        assert len(target_tweet_medias) == 0

    @nose2.tools.params(
        ('rt', 7),
        ('fav', 6),
        ('rtfav', 10),
        ('rrrt', 7),
        ('mixed', 3),
    )
    def test_get_target_tweets(self, mode: str, count: int) -> None:
        self.mock_cursor.pages.side_effect = MockTweepyCursor.pages
        self.mock_instagram.get_media_urls.return_value = [INSTAGRAM_DUMMY_URL]
        self.twitter.mode = mode
        target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_target_tweets(self.user)

        assert len(target_tweet_medias) == count
        for tweet_id, tweet_media in target_tweet_medias.items():
            assert isinstance(tweet_id, str)
            assert isinstance(tweet_media, TweetMedia)
