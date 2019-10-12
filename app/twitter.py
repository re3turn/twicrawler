#!/usr/bin/python3

import re
import traceback
import tweepy
import time
from typing import Iterator, List
from app.env import Env
from app.instagram import Instagram


class TwitterUser(object):
    def __init__(self, user_id: str) -> None:
        self.id = user_id
        self.since_id = 1


class Twitter:
    def __init__(self) -> None:
        self.tweet_page: int = int(Env.get_environment('TWEET_PAGES', default='25'))
        self.tweet_count: int = int(Env.get_environment('TWEET_COUNT', default='200'))
        self.mode: str = Env.get_environment('MODE_SPECIFIED', default='rt')
        self._last_fav_result: dict = {}

        consumer_key: str = Env.get_environment('TWITTER_CONSUMER_KEY', required=True)
        consumer_secret: str = Env.get_environment('TWITTER_CONSUMER_SECRET', required=True)
        access_token: str = Env.get_environment('TWITTER_ACCESS_TOKEN', required=True)
        access_token_secret: str = Env.get_environment('TWITTER_ACCESS_TOKEN_SECRET', required=True)

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, retry_count=3, retry_delay=5, retry_errors={500, 503}, wait_on_rate_limit=True,
                              wait_on_rate_limit_notify=True)

    @staticmethod
    def make_original_image_url(url: str) -> str:
        if '?' in url:
            image_url = re.sub('name=[a-z0-9]+', 'name=orig', url)
            return image_url

        return url + '?name=orig'

    @staticmethod
    def limit_handled(page: tweepy.cursor.IdIterator) -> Iterator[tweepy.models.ResultSet]:
        while True:
            try:
                yield page.next()
            except StopIteration:
                break

    @staticmethod
    def is_quoted(tweet: tweepy.models.Status) -> bool:
        return tweet.is_quote_status

    @staticmethod
    def _get_photo_url(media: dict) -> str:
        if 'media_url_https' in media:
            return media['media_url_https']
        elif 'media_url' in media:
            return media['media_url']

        return ""

    @staticmethod
    def _get_video_url(media: dict) -> str:
        bitrate = 0
        index = 0
        for i, video in enumerate(media['video_info']['variants']):
            if 'bitrate' in video and video['bitrate'] > bitrate:
                bitrate = video['bitrate']
                index = i

        if bitrate > 0:
            return media['video_info']['variants'][index]['url']

        return ""

    @staticmethod
    def _has_instagram_url(entities: dict) -> bool:
        if 'urls' not in entities:
            return False

        for url in entities['urls']:
            if 'expanded_url' in url and url['expanded_url'].startswith('https://www.instagram.com'):
                return True
            elif 'url' in url and url['url'].startswith('https://www.instagram.com'):
                return True

        return False

    @staticmethod
    def _get_instagram_url(entities: dict) -> str:
        for url in entities['urls']:
            if 'expanded_url' in url and url['expanded_url'].startswith('https://www.instagram.com'):
                return url['expanded_url']
            elif 'url' in url and url['url'].startswith('https://www.instagram.com'):
                return url['url']

        return ""

    def _get_twitter_media_urls(self, extended_entities: dict) -> List[str]:
        if 'media' not in extended_entities:
            return []

        media_url_list = []
        url = ""
        for media in extended_entities['media']:
            if media['type'] == 'photo':
                url = self._get_photo_url(media)
            elif media['type'] == 'video':
                url = self._get_video_url(media)

            if url:
                media_url_list.append(url)

        return media_url_list

    def get_media_tweets(self, tweet: tweepy.Status) -> dict:
        # TODO: -> Dict[str, Tuple[tweepy.Status, List[str]]]
        media_tweet_dict = {}

        tweet_status = tweet
        if hasattr(tweet, 'retweeted_status'):
            tweet_status = tweet.retweeted_status

        if self.is_quoted(tweet_status) and hasattr(tweet_status, 'quoted_status'):
            media_tweet_dict.update(self.get_media_tweets(tweet_status.quoted_status))

        if hasattr(tweet_status, 'extended_entities') and 'media' in tweet_status.extended_entities:
            media_type = 'Twitter'
        elif hasattr(tweet_status, 'entities') and self._has_instagram_url(tweet_status.entities):
            media_type = 'Instagram'
        else:
            return {}

        if media_type == 'Twitter':
            extended_entities = tweet_status.extended_entities
            media_url_list = self._get_twitter_media_urls(extended_entities)
        elif media_type == 'Instagram':
            media_url_list = Instagram(self._get_instagram_url(tweet_status.entities)).get_media_urls()
        else:
            return {}

        tweet_status_media_dict = dict(tweet_status=tweet_status, urls=media_url_list)

        media_tweet_dict[tweet_status.id_str] = tweet_status_media_dict

        return media_tweet_dict

    @staticmethod
    def make_tweet_permalink(tweet_status: tweepy.models.Status) -> str:
        return f'https://twitter.com/{tweet_status.user.screen_name}/status/{tweet_status.id_str}'

    @staticmethod
    def make_tweet_description(tweet_status: tweepy.models.Status) -> str:
        return f'{tweet_status.user.name}\n' \
               f'@{tweet_status.user.screen_name}\n' \
               f'{tweet_status.full_text}'

    @classmethod
    def show_media_info(cls, tweet_status_media_dict: dict) -> None:
        tweet_status = tweet_status_media_dict['tweet_status']
        urls = tweet_status_media_dict['urls']
        print(f'user_id={tweet_status.user.screen_name}, tweet_date={str(tweet_status.created_at)}, '
              f'permalink={cls.make_tweet_permalink(tweet_status)}, media_urls={urls}')

    @classmethod
    def show_media_infos(cls, media_tweet_dict: dict) -> None:
        for _, tweet_status_media_dict in media_tweet_dict.items():
            cls.show_media_info(tweet_status_media_dict)

    def show_tweet_media(self, tweet: tweepy.models.Status) -> None:
        print('################## ', self.make_tweet_permalink(tweet))
        medias: dict = {}
        try:
            medias = self.get_media_tweets(tweet)
        except Exception as e:
            print(e.args)
            traceback.print_exc()
        if medias:
            self.show_media_infos(medias)
        else:
            print('no media')

    def show_favorite_tweet_media(self, user: TwitterUser) -> None:
        for tweets in self.limit_handled(tweepy.Cursor(self.api.favorites,
                                                       id=user.id,
                                                       tweet_mode='extended').pages(self.tweet_page)):
            for tweet in tweets:
                self.show_tweet_media(tweet)

    def get_favorite_media(self, user: TwitterUser) -> dict:
        media_tweet_dicts = {}
        for tweets in self.limit_handled(tweepy.Cursor(self.api.favorites,
                                                       id=user.id,
                                                       count=self.tweet_count,
                                                       tweet_mode="extended").pages(self.tweet_page)):
            for tweet in tweets:
                media_tweet_dict: dict = {}
                try:
                    media_tweet_dict = self.get_media_tweets(tweet)
                except Exception as e:
                    print(e.args)
                    traceback.print_exc()

                if media_tweet_dict:
                    media_tweet_dicts.update(media_tweet_dict)

        return media_tweet_dicts

    def show_rt_media(self, user: TwitterUser) -> None:
        for tweets in self.limit_handled(tweepy.Cursor(self.api.user_timeline,
                                                       id=user.id,
                                                       tweet_mode='extended',
                                                       count=self.tweet_count,
                                                       since_id=user.since_id).pages(self.tweet_page)):
            if user.since_id < tweets.since_id:
                user.since_id = tweets.since_id

            for tweet in tweets:
                if not hasattr(tweet, 'retweeted_status'):
                    continue
                if not tweet.retweeted_status:
                    continue
                self.show_tweet_media(tweet)

    def get_rt_media(self, user: TwitterUser) -> dict:
        media_tweet_dicts = {}
        for tweets in self.limit_handled(tweepy.Cursor(self.api.user_timeline,
                                                       id=user.id,
                                                       tweet_mode='extended',
                                                       count=self.tweet_count,
                                                       since_id=user.since_id).pages(self.tweet_page)):
            if user.since_id < tweets.since_id:
                user.since_id = tweets.since_id

            for tweet in tweets:
                if not hasattr(tweet, 'retweeted_status'):
                    continue
                if not tweet.retweeted_status:
                    continue
                if 'mixed' in self.mode:
                    if not hasattr(tweet, 'favorited'):
                        continue
                    if not tweet.favorited:
                        continue
                media_tweet_dict = None
                try:
                    media_tweet_dict = self.get_media_tweets(tweet)
                except Exception as e:
                    print(e.args)
                    traceback.print_exc()

                if media_tweet_dict:
                    media_tweet_dicts.update(media_tweet_dict)

        return media_tweet_dicts

    def get_target_tweets(self, user: TwitterUser) -> dict:
        target_tweets_dict = {}
        if 'fav' in self.mode:
            new_fav_result = self.get_favorite_media(user)
            # valueにdict(unhashable)があるためitems()で差集合が計算できない。ので、keys()で計算する。
            diff_keys = new_fav_result.keys() - self._last_fav_result.keys()
            target_tweets_dict.update({k:new_fav_result[k] for k in diff_keys})
            self._last_fav_result = new_fav_result
        if 'rt' in self.mode or 'mixed' in self.mode:
            target_tweets_dict.update(self.get_rt_media(user))
        return target_tweets_dict


if __name__ == '__main__':
    twitter_user = TwitterUser(user_id='TwitterJP')
    t = Twitter()
    t.show_rt_media(twitter_user)
