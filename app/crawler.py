#!/usr/bin/python3

import os
import re
import sys
import time
import traceback
import urllib

from googleapiclient.errors import HttpError
from retry import retry

from app.env import Env
from app.google_photos import GooglePhotos
from app.store import Store
from app.twitter import Twitter, TwitterUser


class Crawler:
    def __init__(self):
        self.twitter = Twitter()
        self.store = Store()
        self.google_photos = GooglePhotos()
        self._download_dir = './download'
        os.makedirs(self._download_dir, exist_ok=True)

    @staticmethod
    @retry(urllib.error.HTTPError, tries=3, delay=1)
    def download_media(media_url, download_path):
        urllib.request.urlretrieve(media_url, download_path)

    def upload_google_photos(self, media_path, description):
        while True:
            try:
                self.google_photos.upload_media(media_path, description)
            except HttpError as error:
                print(f'HTTP status={error.resp.reason}', file=sys.stderr)
                traceback.print_exc()
                return False
            except Exception as error:
                print(f'Error reason={error}', file=sys.stderr)
                traceback.print_exc()
                return False

            break

        return True

    def make_download_path(self, url):
        url = re.sub('\?.*$', '', url)
        return f'{self._download_dir}/{os.path.basename(url)}'

    def backup_media(self, media_tweet_dicts):
        for tweet_id, tweet_status_media_dict in media_tweet_dicts.items():
            tweet_status = tweet_status_media_dict['tweet_status']
            if self.store.is_added_tweet(tweet_id):
                continue
            Twitter.show_media_info(tweet_status_media_dict)
            for url in tweet_status_media_dict['urls']:
                # download
                download_path = self.make_download_path(url)
                if url.startswith("https://pbs.twimg.com/media") or url.startswith("http://pbs.twimg.com/media"):
                    url = self.twitter.make_original_image_url(url)
                try:
                    Crawler.download_media(url, download_path)
                except urllib.error.HTTPError as e:
                    traceback.print_exc()
                    print(f'download failed. tweet_id={tweet_id}, media_url={url}', file=sys.stderr)
                    continue

                # upload
                is_uploaded = self.upload_google_photos(download_path, Twitter.make_tweet_description(tweet_status))
                if not is_uploaded:
                    print(f'upload failed. tweet_id={tweet_id}, media_url={url}', file=sys.stderr)
                    continue

                # delete
                os.remove(download_path)

            # store update
            try:
                self.store.insert_tweet_info(tweet_id, tweet_status.user.screen_name, str(tweet_status.created_at))
            except Exception as e:
                print(f'Insert failed. tweet_id={tweet_id}', e.args, file=sys.stderr)
                traceback.print_exc()

    def crawling_rt(self, user):
        media_tweet_dicts = self.twitter.get_rt_media(user)
        self.backup_media(media_tweet_dicts)

    def main(self):
        interval_minutes = int(Env.get_environment('INTERVAL', default='5'))
        user_ids = Env.get_environment('TWITTER_USER_IDS')

        user_list = [TwitterUser(user_id) for user_id in user_ids.split(',')]

        while True:
            try:
                for user in user_list:
                    self.crawling_rt(user)
            except:
                traceback.print_exc()

            time.sleep(interval_minutes * 60)


if __name__ == '__main__':
    crawler = Crawler()
    crawler.main()
