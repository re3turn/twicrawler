#!/usr/bin/python3

import argparse
import inspect
import json
import os
import requests
import tweepy

from typing import Dict, Any, List, Tuple

from app.instagram import Instagram
from app.twitter import Twitter, TweetMedia, TwitterUser

TEST_USER_ID: str = 'TwicrawlerT'
TEST_TWEET_COUNT = 200
JSON_DIR = f'{os.path.dirname(__file__)}/../json'
FUNC_NAME = 0


class TwitterJson:
    def __init__(self, user_id: str) -> None:
        self.user: TwitterUser = TwitterUser(id=user_id)
        self.tweet: TwitterJson.Tweet = self.Tweet()
        self.tweets: TwitterJson.Tweets = self.Tweets(self.user)
        self.target_tweet_medias: TwitterJson.TargetTweetMedias = self.TargetTweetMedias(self.user)

    @staticmethod
    def json_dump_default(obj: object) -> Any:
        if isinstance(obj, TweetMedia) and hasattr(obj, '__dict__'):
            return obj.__dict__
        if isinstance(obj, tweepy.Status) and hasattr(obj, '_json'):
            # noinspection PyProtectedMember
            return obj._json
        return json.JSONEncoder().default(obj)

    class Tweet:
        @staticmethod
        def make(tweet_id: str, json_name: str) -> None:
            tweet = Twitter().api.get_status(id=tweet_id, tweet_mode='extended')
            json_path = f'{JSON_DIR}/twitter/tweet/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(tweet, f, default=TwitterJson.json_dump_default, indent=2)

        @staticmethod
        def make_illegal_extended_url(tweet_id: str, json_name: str) -> None:
            tweet = Twitter().api.get_status(id=tweet_id, tweet_mode='extended')
            for i, _ in enumerate(tweet.entities['urls']):
                tweet.entities['urls'][i]['url'] = tweet.entities['urls'][0]['expanded_url']
                tweet.entities['urls'][i]['expanded_url'] = ''
            json_path = f'{JSON_DIR}/twitter/tweet/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(tweet, f, default=TwitterJson.json_dump_default, indent=2)

        @staticmethod
        def make_illegal_video_info(tweet_id: str, json_name: str) -> None:
            tweet = Twitter().api.get_status(id=tweet_id, tweet_mode='extended')
            for i, _ in enumerate(tweet.extended_entities['media']):
                tweet.extended_entities['media'][i]['video_info']['variants'] = []
            json_path = f'{JSON_DIR}/twitter/tweet/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(tweet, f, default=TwitterJson.json_dump_default, indent=2)

        @staticmethod
        def make_illegal_media_url(tweet_id: str, json_name: str) -> None:
            tweet = Twitter().api.get_status(id=tweet_id, tweet_mode='extended')
            for i, _ in enumerate(tweet.extended_entities['media']):
                del tweet.extended_entities['media'][i]['media_url']
                del tweet.extended_entities['media'][i]['media_url_https']
            json_path = f'{JSON_DIR}/twitter/tweet/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(tweet, f, default=TwitterJson.json_dump_default, indent=2)

    class Tweets:
        def __init__(self, user: TwitterUser) -> None:
            self.user: TwitterUser = user

        def make(self, json_name: str) -> None:
            self.user.since_id = 1
            tweets: list
            if json_name == 'timeline':
                tweets = Twitter().api.user_timeline(id=TEST_USER_ID, count=TEST_TWEET_COUNT, tweet_mode="extended")
            elif json_name == 'fav':
                tweets = Twitter().api.favorites(id=TEST_USER_ID, count=TEST_TWEET_COUNT, tweet_mode="extended")
            else:
                return

            json_path = f'{JSON_DIR}/twitter/tweets/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(tweets, f, default=TwitterJson.json_dump_default, indent=2)

    class TargetTweetMedias:
        def __init__(self, user: TwitterUser) -> None:
            self.user: TwitterUser = user

        def make(self, json_name: str) -> None:
            mode: str = json_name
            self.user.since_id = 1
            os.environ['MODE_SPECIFIED'] = mode
            target_tweet_medias: Dict[str, TweetMedia] = Twitter().get_target_tweets(self.user)
            json_path = f'{JSON_DIR}/twitter/target_tweet_medias/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(target_tweet_medias, f, default=TwitterJson.json_dump_default, indent=2)


class InstagramJson:
    class Post:
        @staticmethod
        def make(url: str) -> None:
            json_path = f'{JSON_DIR}/instagram/post/{os.path.basename(url.rstrip("/"))}.json'
            # noinspection PyProtectedMember
            json_data: dict = Instagram(url)._get_json_data()
            with open(json_path, 'w', newline='\n') as f:
                json.dump(json_data, f, indent=2)

    class UrlContent:
        @staticmethod
        def make(url: str) -> None:
            json_path = f'{JSON_DIR}/instagram/url_content/{os.path.basename(url.rstrip("/"))}.json'
            response: requests.models.Response = requests.get(url)
            json_data = {'content': response.content.decode('utf-8')}
            with open(json_path, 'w', newline='\n') as f:
                json.dump(json_data, f, indent=2)


class CrawlerJson:
    class FailedUploadMedia:
        @staticmethod
        def fetch_failed_upload_media(tweet_id: str) -> List[Tuple[str, str]]:
            twitter = Twitter()
            tweet: tweepy.Status = twitter.api.get_status(id=tweet_id, tweet_mode='extended')
            tweet_medias: Dict[str, TweetMedia] = twitter.get_tweet_medias(tweet)
            tweet_media: TweetMedia = tweet_medias[tweet_id]
            failed_upload_media: List[Tuple[str, str]] = []
            description: str = Twitter.make_tweet_description(tweet)
            for url in tweet_media.urls:
                failed_upload_media.append((url, description))

            return failed_upload_media

        @classmethod
        def make(cls, tweet_id: str, json_name: str) -> None:
            failed_upload_media: List[Tuple[str, str]] = cls.fetch_failed_upload_media(tweet_id)

            json_path = f'{JSON_DIR}/crawler/failed_upload_media/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(failed_upload_media, f, indent=2)

    class StoreFailedUploadMedia:
        @staticmethod
        def make(tweet_id: str, json_name: str) -> None:
            failed_upload_media: list = CrawlerJson.FailedUploadMedia.fetch_failed_upload_media(tweet_id)
            fetch_all_failed_upload_media: List[Tuple[str, str, str]] = []
            for url, description in failed_upload_media:
                fetch_all_failed_upload_media.append((url, description, tweet_id))

            json_path = f'{JSON_DIR}/crawler/fetch_all_failed_upload_media/{json_name}.json'
            with open(json_path, 'w', newline='\n') as f:
                json.dump(fetch_all_failed_upload_media, f, indent=2)


class Module:
    @staticmethod
    def twitter() -> None:
        twitter_json: TwitterJson = TwitterJson(TEST_USER_ID)

        twitter_json.target_tweet_medias.make(json_name='fav')

        # The favorited status is valid only for the API owner, so only API owners should create timeline JSON
        twitter_json.tweets.make(json_name='timeline')
        twitter_json.tweets.make(json_name='fav')

        twitter_json.tweet.make(tweet_id='1184511270378061824', json_name='has_images')
        twitter_json.tweet.make(tweet_id='1187057372767801346', json_name='has_not_images')
        twitter_json.tweet.make(tweet_id='1188832511515750404', json_name='has_video')
        twitter_json.tweet.make(tweet_id='1184510376081272833', json_name='has_instagram_url')
        twitter_json.tweet.make(tweet_id='1187057599616651264', json_name='is_fav_rt_quoted')
        twitter_json.tweet.make(tweet_id='1187057372767801346', json_name='is_not_fav_rt_quoted')
        twitter_json.tweet.make_illegal_media_url(tweet_id='1184511270378061824', json_name='has_illegal_images')
        twitter_json.tweet.make_illegal_video_info(tweet_id='1188832511515750404', json_name='has_illegal_video')
        twitter_json.tweet.make_illegal_extended_url(tweet_id='1184510376081272833',
                                                     json_name='has_illegal_instagram_url')

    @staticmethod
    def instagram() -> None:
        InstagramJson.Post.make(url='https://www.instagram.com/p/B0v8aXWg8aG/')  # Single photos
        InstagramJson.Post.make(url='https://www.instagram.com/p/BcDPlNZhhRC/')  # Multi photos
        InstagramJson.Post.make(url='https://www.instagram.com/p/B0q8HJ0hiQ9/')  # Videos

        InstagramJson.UrlContent.make(url='https://www.instagram.com/p/B0v8aXWg8aG/')  # Single photos
        InstagramJson.UrlContent.make(url='https://www.instagram.com/p/BcDPlNZhhRC/')  # Multi photos
        InstagramJson.UrlContent.make(url='https://www.instagram.com/p/B0q8HJ0hiQ9/')  # Videos

    @staticmethod
    def google_photos() -> None:
        # Do not create JSON for Google_Photos test because there is no way to delete data uploaded with Google API
        pass

    @staticmethod
    def crawler() -> None:
        CrawlerJson.FailedUploadMedia.make(tweet_id='1188832511515750404', json_name='one')
        CrawlerJson.FailedUploadMedia.make(tweet_id='1184510376081272833', json_name='three')

        CrawlerJson.StoreFailedUploadMedia.make(tweet_id='1188832511515750404', json_name='one')
        CrawlerJson.StoreFailedUploadMedia.make(tweet_id='1184510376081272833', json_name='three')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Make test json file')
    parser.add_argument('-m', '--module', default='all', help='module name')
    args = parser.parse_args()

    modules = [func_info[FUNC_NAME] for func_info in inspect.getmembers(Module, inspect.isfunction)]

    if args.module == 'all':
        for module in modules:
            print(f'Make json(module = {module})')
            eval(f'Module.{module}')()
    elif args.module in modules:
        print(f'Make json(module = {args.module})')
        eval(f'Module.{args.module}')()
