#!/usr/bin/python3

import os
import re
import shutil
import sys
import time
import traceback
import urllib.request
import urllib.error

import tweepy
from googleapiclient.errors import HttpError
from retry import retry
from typing import List, Tuple, Dict

from app.env import Env
from app.google_photos import GooglePhotos
from app.store import Store
from app.twitter import Twitter, TwitterUser, TweetMedia


class Crawler:
    def __init__(self) -> None:
        self._save_mode: str = Env.get_environment('SAVE_MODE', default='local')
        self.twitter: Twitter = Twitter()
        self.store: Store = Store()
        if self._save_mode == 'google':
            self.google_photos: GooglePhotos = GooglePhotos()
        self._download_dir: str = './download'

        os.makedirs(self._download_dir, exist_ok=True)

    @staticmethod
    @retry(urllib.error.HTTPError, tries=3, delay=2, backoff=2)
    def download_media(media_url: str, download_path: str) -> None:
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        urllib.request.urlretrieve(media_url, download_path)

    def upload_google_photos(self, media_path: str, description: str) -> bool:
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

    def make_download_path(self, url: str, user_id: str) -> str:
        url = re.sub(r'\?.*$', '', url)
        return f'{self._download_dir}/{user_id}/{os.path.basename(url)}'

    def save_media(self, url: str, description: str, user_id: str) -> bool:
        # download
        download_path: str = self.make_download_path(url, user_id)
        if url.startswith('https://pbs.twimg.com/media') or url.startswith('http://pbs.twimg.com/media'):
            url = self.twitter.make_original_image_url(url)
        try:
            self.download_media(url, download_path)
        except urllib.error.HTTPError:
            traceback.print_exc()
            print(f'download failed. media_url={url}', file=sys.stderr)
            return False

        if self._save_mode == 'local':
            return True

        # upload
        is_uploaded: bool = self.upload_google_photos(download_path, description)

        # delete
        shutil.rmtree(os.path.dirname(download_path))

        if not is_uploaded:
            print(f'upload failed. media_url={url}', file=sys.stderr)
            return False

        return True

    def backup_media(self, tweet_medias: Dict[str, TweetMedia]) -> None:
        if not tweet_medias:
            return

        target_tweet_ids = self.store.fetch_not_added_tweets(list(tweet_medias.keys()))
        for tweet_id, in target_tweet_ids:
            target_tweet_media: TweetMedia = tweet_medias[tweet_id]
            target_tweet: tweepy.Status = target_tweet_media.tweet
            failed_upload_medias: List[Tuple[str, str]] = []

            target_tweet_media.show_info()
            for url in target_tweet_media.urls:
                description: str = Twitter.make_tweet_description(target_tweet)
                is_saved: bool = self.save_media(url, description, target_tweet.user.screen_name)
                if not is_saved:
                    failed_upload_medias.append((url, description))
                    print(f'Save failed. tweet_id={tweet_id}, media_url={url}', file=sys.stderr)
                    continue

            # store update
            try:
                self.store.insert_tweet_info(tweet_id, target_tweet.user.screen_name, str(target_tweet.created_at))
            except Exception as e:
                print(f'Insert failed. tweet_id={tweet_id}', e.args, file=sys.stderr)
                traceback.print_exc()

            if not failed_upload_medias:
                continue

            # store failed upload media
            for failed_url, description in failed_upload_medias:
                try:
                    self.store.insert_failed_upload_media(failed_url, description, target_tweet.user.screen_name)
                except Exception as e:
                    print(f'Insert failed. failed_url={failed_url}, description={description}',
                          e.args, file=sys.stderr)
                    traceback.print_exc()

    def retry_backup_media(self) -> None:
        url: str = ''
        try:
            for url, description, user_id in self.store.fetch_all_failed_upload_medias():
                is_saved: bool = self.save_media(url, description, user_id)
                if not is_saved:
                    print(f'Retry Save failed. media_url={url}', file=sys.stderr)
                    continue
                self.store.delete_failed_upload_media(url)
        except Exception as e:
            print(f'Retry backup failed. failed_url={url}', e.args, file=sys.stderr)
            traceback.print_exc()

    def crawling_tweets(self, user: TwitterUser) -> None:
        target_tweet_medias: Dict[str, TweetMedia] = self.twitter.get_target_tweets(user)
        self.backup_media(target_tweet_medias)
        self.retry_backup_media()

    def main(self) -> None:
        interval_minutes: int = int(Env.get_environment('INTERVAL', default='5'))
        user_ids: str = Env.get_environment('TWITTER_USER_IDS', required=True)

        user_list: List[TwitterUser] = [TwitterUser(id=user_id) for user_id in user_ids.split(',')]

        while True:
            try:
                for user in user_list:
                    self.crawling_tweets(user)
            except Exception as e:
                print(e.args)
                traceback.print_exc()

            time.sleep(interval_minutes * 60)


if __name__ == '__main__':
    crawler = Crawler()
    crawler.main()
