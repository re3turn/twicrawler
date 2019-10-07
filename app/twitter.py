#!/usr/bin/python3

import os
import re
import sys
import traceback
import tweepy
import time

from app.env import Env
from app.instagram import Instagram


class Twitter:
    def __init__(self):
        self.tweet_page = int(Env.get_environment('TWEET_PAGES', default='25'))
        self.tweet_count = int(Env.get_environment('TWEET_COUNT', default='200'))
        self.mode = Env.get_environment('MODE_SPECIFIED', default='rt')

        consumer_key = Env.get_environment('TWITTER_CONSUMER_KEY', required=True)
        consumer_secret = Env.get_environment('TWITTER_CONSUMER_SECRET', required=True)
        access_token = Env.get_environment('TWITTER_ACCESS_TOKEN', required=True)
        access_token_secret = Env.get_environment('TWITTER_ACCESS_TOKEN_SECRET', required=True)

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit=True)

    @staticmethod
    def make_original_image_url(url):
        if "?" in url:
            image_url = re.sub('name=[a-z0-9]+', 'name=orig', url)
            return image_url

        return url + "?name=orig"

    @staticmethod
    def limit_handled(page):
        while True:
            try:
                yield page.next()
            except tweepy.RateLimitError:
                time.sleep(15 * 60)
            except StopIteration:
                break

    @staticmethod
    def is_quoted(tweet):
        return tweet.is_quote_status

    @staticmethod
    def _get_photo_url(media):
        if 'media_url_https' in media:
            return media['media_url_https']
        elif 'media_url' in media:
            return media['media_url']

        return ""

    @staticmethod
    def _get_video_url(media):
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
    def _has_instagram_url(entities):
        if 'urls' not in entities:
            return False

        for url in entities['urls']:
            if 'expanded_url' in url and url['expanded_url'].startswith("https://www.instagram.com"):
                return True
            elif 'url' in url and url['url'].startswith("https://www.instagram.com"):
                return True

        return False

    @staticmethod
    def _get_instagram_url(entities):
        for url in entities['urls']:
            if 'expanded_url' in url and url['expanded_url'].startswith("https://www.instagram.com"):
                return url['expanded_url']
            elif 'url' in url and url['url'].startswith("https://www.instagram.com"):
                return url['url']

        return ""

    def _get_twitter_media_urls(self, extended_entities):
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

    def get_media_tweets(self, tweet):
        media_tweet_dict = {}

        if self.is_quoted(tweet) and hasattr(tweet, "quoted_status"):
            media_tweet_dict.update(self.get_media_tweets(tweet.quoted_status))

        tweet_status = tweet
        if tweet.retweeted and hasattr(tweet, "retweeted_status"):
            tweet_status = tweet.retweeted_status

        if hasattr(tweet_status, "extended_entities") and 'media' in tweet_status.extended_entities:
            media_type = "Twitter"
        elif hasattr(tweet_status, "entities") and self._has_instagram_url(tweet_status.entities):
            media_type = "Instagram"
        else:
            return {}

        if media_type == "Twitter":
            extended_entities = tweet_status.extended_entities
            media_url_list = self._get_twitter_media_urls(extended_entities)
        elif media_type == "Instagram":
            media_url_list = Instagram(self._get_instagram_url(tweet_status.entities)).get_media_urls()

        tweet_status_media_dict = {'tweet_status': tweet_status,
                                    'urls': media_url_list
                                  }

        media_tweet_dict[tweet_status.id_str] = tweet_status_media_dict

        return media_tweet_dict

    @staticmethod
    def make_tweet_permalink(tweet_status):
        return f'https://twitter.com/{tweet_status.user.screen_name}/status/{tweet_status.id_str}'

    @staticmethod
    def make_tweet_description(tweet_status):
        return f'{tweet_status.user.name}\n' \
               f'@{tweet_status.user.screen_name}\n' \
               f'{tweet_status.full_text}'

    @classmethod
    def show_media_info(cls, tweet_status_media_dict):
        tweet_status = tweet_status_media_dict['tweet_status']
        urls = tweet_status_media_dict['urls']
        print(f'user_id={tweet_status.user.screen_name}, tweet_date={str(tweet_status.created_at)}, '
              f'permalink={cls.make_tweet_permalink(tweet_status)}, media_urls={urls}')

    @classmethod
    def show_media_infos(cls, media_tweet_dict):
        for _, tweet_status_media_dict in media_tweet_dict.items():
            cls.show_media_info(tweet_status_media_dict)

    def show_favorite_tweet_media(self, user):
        for tweets in self.limit_handled(tweepy.Cursor(self.api.favorites,
                                                       id=user.id,
                                                       tweet_mode="extended").pages(self.tweet_page)):
            for tweet in tweets:
                print('################## ', tweet.id_str)
                medias = {}
                try:
                    medias = self.get_media_tweets(tweet)
                except Exception as e:
                    traceback.print_exc()

                if medias:
                    self.show_media_infos(medias)
                else:
                    print('no media')

    def get_favorite_media(self, user: str):
        media_tweet_dicts = {}
        for tweets in self.limit_handled(tweepy.Cursor(self.api.favorites,
                                                       id=user.id,
                                                       count=self.tweet_count,
                                                       tweet_mode="extended").pages(self.tweet_page)):
            for tweet in tweets:
                media_tweet_dict = None
                try:
                    media_tweet_dict = self.get_media_tweets(tweet)
                except:
                    traceback.print_exc()

                if media_tweet_dict:
                    media_tweet_dicts.update(media_tweet_dict)

        return media_tweet_dicts

    def show_rt_media(self, user):
        for tweets in self.limit_handled(tweepy.Cursor(self.api.user_timeline,
                                                       id=user.id,
                                                       tweet_mode="extended",
                                                       count=self.tweet_count,
                                                       since_id=user.since_id).pages(self.tweet_page)):
            if user.since_id < tweets.since_id:
                user.since_id = tweets.since_id

            for tweet in tweets:
                if not hasattr(tweet, "retweeted_status"):
                    continue
                if not tweet.retweeted_status:
                    continue
                print('################## ', tweet.id_str)
                medias = {}
                try:
                    medias = self.get_media_tweets(tweet)
                except:
                    traceback.print_exc()
                if medias:
                    self.show_media_infos(medias)
                else:
                    print('no media')

    def get_rt_media(self, user):
        media_tweet_dicts = {}
        for tweets in self.limit_handled(tweepy.Cursor(self.api.user_timeline,
                                                       id=user.id,
                                                       tweet_mode="extended",
                                                       count=self.tweet_count,
                                                       since_id=user.since_id).pages(self.tweet_page)):
            if user.since_id < tweets.since_id:
                user.since_id = tweets.since_id

            for tweet in tweets:
                if not hasattr(tweet, "retweeted_status"):
                    continue
                if not tweet.retweeted_status:
                    continue
                if 'mixed' in self.mode and not hasattr(tweet, "favorited"):
                    continue

                try:
                    media_tweet_dict = self.get_media_tweets(tweet)
                except:
                    traceback.print_exc()

                if media_tweet_dict:
                    media_tweet_dicts.update(media_tweet_dict)

        return media_tweet_dicts

    def get_target_tweets(self, user):
        target_tweets_dict = {}
        if 'fav' in self.mode:
            target_tweets_dict.update(self.get_favorite_media(user))
        if 'rt' in self.mode or 'mixed' in self.mode:
            target_tweets_dict.update(self.get_rt_media(user))
        return target_tweets_dict


class TwitterUser:
    def __init__(self, user_id):
        self.id = user_id
        self.since_id = 1


if __name__ == '__main__':
    twitter_user = TwitterUser(user_id="TwitterJP")
    t = Twitter()
    t.show_rt_media(twitter_user)
