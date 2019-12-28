#!/usr/bin/python3

import dataclasses
import logging
import re
import tweepy

from typing import Iterator, List, Dict

from app.env import Env
from app.instagram import Instagram
from app.log import Log


@dataclasses.dataclass
class TwitterUser(object):
    id: str = ''
    since_id: int = 1


@dataclasses.dataclass
class TweetMedia(object):
    urls: List[str]
    tweet: tweepy.Status

    def show_info(self) -> None:
        tweet: tweepy.Status = self.tweet
        urls: List[str] = self.urls
        logger.info(f'user_id={tweet.user.screen_name}, tweet_date={str(tweet.created_at)}, '
                    f'permalink={Twitter.make_tweet_permalink(tweet)}, media_urls={urls}')


class Twitter:
    def __init__(self) -> None:
        self.tweet_page: int = int(Env.get_environment('TWEET_PAGES', default='25'))
        self.tweet_count: int = int(Env.get_environment('TWEET_COUNT', default='200'))
        self.mode: str = Env.get_environment('MODE_SPECIFIED', default='rt')
        self._last_fav_result: Dict[str, TweetMedia] = {}

        consumer_key: str = Env.get_environment('TWITTER_CONSUMER_KEY', required=True)
        consumer_secret: str = Env.get_environment('TWITTER_CONSUMER_SECRET', required=True)
        access_token: str = Env.get_environment('TWITTER_ACCESS_TOKEN', required=True)
        access_token_secret: str = Env.get_environment('TWITTER_ACCESS_TOKEN_SECRET', required=True)

        auth: tweepy.OAuthHandler = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api: tweepy.API = tweepy.API(auth, retry_count=3, retry_delay=5, retry_errors={500, 503},
                                          wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

        logger.debug(f'Twitter setting info. tweet_page={self.tweet_page}, tweet_count={self.tweet_count}, '
                     f'mode={self.mode}')

    @staticmethod
    def make_original_image_url(url: str) -> str:
        if '?' in url:
            if 'name=' in url:
                original_url: str = re.sub('name=[a-zA-Z0-9]+', 'name=orig', url)
                return original_url
            else:
                return url + '&name=orig'

        return url + '?name=orig'

    @staticmethod
    def is_quoted(tweet: tweepy.Status) -> bool:
        target_tweet = tweet
        if hasattr(tweet, 'retweeted_status'):
            target_tweet = tweet.retweeted_status
        if not hasattr(target_tweet, 'quoted_status'):
            return False
        if not target_tweet.quoted_status:
            return False
        return True

    @staticmethod
    def is_favorited(tweet: tweepy.Status) -> bool:
        target_tweet = tweet
        if hasattr(tweet, 'retweeted_status'):
            target_tweet = tweet.retweeted_status
        if not hasattr(target_tweet, 'favorited'):
            return False

        return target_tweet.favorited

    @staticmethod
    def is_retweeted(tweet: tweepy.Status) -> object:
        if not hasattr(tweet, 'retweeted_status'):
            return False
        if not tweet.retweeted_status:
            return False
        return True

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

        media_url_list: List[str] = []
        url = ""
        for media in extended_entities['media']:
            if media['type'] == 'photo':
                url = self._get_photo_url(media)
            elif media['type'] == 'video':
                url = self._get_video_url(media)

            if url:
                media_url_list.append(url)

        return media_url_list

    def get_tweet_medias(self, tweet: tweepy.Status) -> Dict[str, TweetMedia]:
        tweet_medias: Dict[str, TweetMedia] = {}

        target_tweet = tweet
        if hasattr(tweet, 'retweeted_status'):
            target_tweet = tweet.retweeted_status

        if self.is_quoted(target_tweet):
            tweet_medias.update(self.get_tweet_medias(target_tweet.quoted_status))

        if hasattr(target_tweet, 'extended_entities') and 'media' in target_tweet.extended_entities:
            media_type = 'Twitter'
        elif hasattr(target_tweet, 'entities') and self._has_instagram_url(target_tweet.entities):
            media_type = 'Instagram'
        else:
            return tweet_medias

        if media_type == 'Twitter':
            extended_entities = target_tweet.extended_entities
            media_url_list = self._get_twitter_media_urls(extended_entities)
        elif media_type == 'Instagram':
            media_url_list = Instagram(self._get_instagram_url(target_tweet.entities)).get_media_urls()
        else:
            return tweet_medias

        tweet_medias[target_tweet.id_str] = TweetMedia(urls=media_url_list, tweet=target_tweet)

        return tweet_medias

    @staticmethod
    def make_tweet_permalink(tweet: tweepy.Status) -> str:
        return f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'

    @staticmethod
    def make_tweet_description(tweet: tweepy.Status) -> str:
        return f'{tweet.user.name}\n' \
               f'@{tweet.user.screen_name}\n' \
               f'{tweet.full_text}'

    @staticmethod
    def difference_tweet_medias(new: Dict[str, TweetMedia], old: Dict[str, TweetMedia]) -> Dict[str, TweetMedia]:
        diff_keys = new.keys() - old.keys()
        return {k: new[k] for k in diff_keys}

    def get_favorite_media(self, user: TwitterUser) -> Dict[str, TweetMedia]:
        logger.info(f'Get favorite tweet media. user={user.id}. pages={self.tweet_page}, count={self.tweet_count}')
        fav_twitter_medias: Dict[str, TweetMedia] = {}
        for tweets in tweepy.Cursor(self.api.favorites,
                                    id=user.id,
                                    count=self.tweet_count,
                                    tweet_mode="extended").pages(self.tweet_page):
            for tweet in tweets:
                tweet_medias: Dict[str, TweetMedia] = {}
                try:
                    tweet_medias = self.get_tweet_medias(tweet)
                except Exception as e:
                    logger.exception(f'Get tweet media error. exception={e.args}')

                if tweet_medias:
                    fav_twitter_medias.update(tweet_medias)

        return fav_twitter_medias

    def get_rt_media(self, user: TwitterUser) -> Dict[str, TweetMedia]:
        logger.info(f'Get RT tweet media. user={user.id}. pages={self.tweet_page}, count={self.tweet_count}, '
                    f'since_id={user.since_id}')
        rt_tweet_medias: Dict[str, TweetMedia] = {}
        for tweets in tweepy.Cursor(self.api.user_timeline,
                                    id=user.id,
                                    tweet_mode='extended',
                                    count=self.tweet_count,
                                    since_id=user.since_id).pages(self.tweet_page):
            if user.since_id < tweets.since_id:
                user.since_id = tweets.since_id

            for tweet in tweets:
                if not self.is_retweeted(tweet):
                    continue
                if 'mixed' in self.mode and (not self.is_favorited(tweet)):
                    continue

                tweet_medias: Dict[str, TweetMedia] = {}
                try:
                    tweet_medias = self.get_tweet_medias(tweet)
                except Exception as e:
                    logger.exception(f'Get tweet media error. exception={e.args}')
                    continue

                if tweet_medias:
                    rt_tweet_medias.update(tweet_medias)

        return rt_tweet_medias

    def get_target_tweets(self, user: TwitterUser) -> dict:
        target_tweet_medias: Dict[str, TweetMedia] = {}
        if 'fav' in self.mode:
            new_fav_result = self.get_favorite_media(user)
            target_tweet_medias.update(self.difference_tweet_medias(new_fav_result, self._last_fav_result))
            self._last_fav_result = new_fav_result
        if 'rt' in self.mode or 'mixed' in self.mode:
            target_tweet_medias.update(self.get_rt_media(user))
        return target_tweet_medias

    class Debug:
        def __init__(self, twitter_obj: object) -> None:
            self.twitter: Twitter = twitter_obj  # type: ignore
            self.api: tweepy.API = self.twitter.api
            self.tweet_page: int = self.twitter.tweet_page
            self.tweet_count: int = self.twitter.tweet_count

        @staticmethod
        def show_media_infos(tweet_medias: Dict[str, TweetMedia]) -> None:
            for _, tweet_media in tweet_medias.items():
                tweet_media.show_info()

        def show_tweet_media(self, tweet: tweepy.Status) -> None:
            logger.info(f'################## {self.twitter.make_tweet_permalink(tweet)}')
            try:
                tweet_medias: Dict[str, TweetMedia] = self.twitter.get_tweet_medias(tweet)
            except Exception as e:
                logger.exception(f'Get tweet media error. exception={e.args}')
                return
            if tweet_medias:
                self.show_media_infos(tweet_medias)
            else:
                logger.info('no media')

        def show_favorite_tweet_media(self, user: TwitterUser) -> None:
            logger.info(f'Show favorite tweet media. user={user.id}. pages={self.tweet_page}, count={self.tweet_count}')
            for tweets in tweepy.Cursor(self.api.favorites,
                                        id=user.id,
                                        count=self.tweet_count,
                                        tweet_mode='extended').pages(self.tweet_page):
                for tweet in tweets:
                    self.show_tweet_media(tweet)

        def show_rt_media(self, user: TwitterUser) -> None:
            logger.info(f'Show RT tweet media. user={user.id}. pages={self.tweet_page}, count={self.tweet_count}, '
                        f'since_id={user.since_id}')
            for tweets in tweepy.Cursor(self.api.user_timeline,
                                        id=user.id,
                                        tweet_mode='extended',
                                        count=self.tweet_count,
                                        since_id=user.since_id).pages(self.tweet_page):
                if user.since_id < tweets.since_id:
                    user.since_id = tweets.since_id

                for tweet in tweets:
                    if not hasattr(tweet, 'retweeted_status'):
                        continue
                    if not tweet.retweeted_status:
                        continue
                    self.show_tweet_media(tweet)


if __name__ == '__main__':
    Log.init_logger(log_name='twitter')
    logger: logging.Logger = logging.getLogger(__name__)
    twitter_user = TwitterUser(id='TwitterJP')
    t = Twitter()
    Twitter.Debug(t).show_rt_media(twitter_user)

logger = logging.getLogger(__name__)
