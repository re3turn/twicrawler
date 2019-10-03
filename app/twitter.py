#!/usr/bin/python3

import os
import re
import sys
import traceback
import tweepy
import time

from app.instagram import Instagram


class Twitter:
    def __init__(self):
        self.tweet_page = int(os.environ.get('TWEET_PAGES', '5'))
        self.tweet_count = int(os.environ.get('TWEET_COUNT', '100'))

        consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
        if consumer_key is None:
            sys.exit('Please set environment "TWITTER_CONSUMER_KEY"')

        consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
        if consumer_secret is None:
            sys.exit('Please set environment "TWITTER_CONSUMER_SECRET"')

        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        if access_token is None:
            sys.exit('Please set environment "TWITTER_ACCESS_TOKEN"')

        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        if access_token_secret is None:
            sys.exit('Please set environment "TWITTER_ACCESS_TOKEN_SECRET"')

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
            media_tweet_dict.update(self.get_media_urls(tweet.quoted_status))

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

        tweet_status_dict = {'user_id': tweet_status.user.screen_name,
                             'tweet_date': str(tweet_status.created_at),
                             'tweet_id': tweet_status.id_str,
                             'urls': media_url_list
                             }

        media_tweet_dict[tweet_status.id_str] = tweet_status_dict

        return media_tweet_dict

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
                    print(medias)
                else:
                    print('no media')

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
                    print(medias)
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

                try:
                    media_tweet_dict = self.get_media_tweets(tweet)
                except:
                    traceback.print_exc()

                if media_tweet_dict:
                    media_tweet_dicts.update(media_tweet_dict)

        return media_tweet_dicts


class TwitterUser:
    def __init__(self, user_id):
        self.id = user_id
        self.since_id = 1


if __name__ == '__main__':
    twitter_user = TwitterUser(user_id="TwitterJP")
    t = Twitter()
    t.show_rt_media(twitter_user)
