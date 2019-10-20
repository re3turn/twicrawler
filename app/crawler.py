#!/usr/bin/python3

import logging
import os
import re
import shutil
import time
import urllib.request
import urllib.error

import tweepy
from googleapiclient.errors import HttpError
from retry import retry
from typing import List, Tuple, Dict

from app.env import Env
from app.google_photos import GooglePhotos
from app.log import Log
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
        logger.debug(f'Download file. url={media_url}, path={download_path}')
        urllib.request.urlretrieve(media_url, download_path)

    def upload_google_photos(self, media_path: str, description: str) -> bool:
        while True:
            try:
                self.google_photos.upload_media(media_path, description)
            except HttpError as error:
                logger.exception(f'HTTP status={error.resp.reason}')
                return False
            except Exception as error:
                logger.exception(f'Error reason={error}')
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
            logger.exception(f'Download failed. media_url={url}')
            return False

        if self._save_mode == 'local':
            return True

        # upload
        is_uploaded: bool = self.upload_google_photos(download_path, description)

        # delete
        shutil.rmtree(os.path.dirname(download_path))
        logger.debug(f'Delete directory. path={os.path.dirname(download_path)}')

        if not is_uploaded:
            logger.error(f'upload failed. media_url={url}')
            return False

        return True

    def backup_media(self, tweet_medias: Dict[str, TweetMedia]) -> None:
        if not tweet_medias:
            logger.info('No new tweet media.')
            return

        target_tweet_ids = self.store.fetch_not_added_tweets(list(tweet_medias.keys()))
        if not target_tweet_ids:
            logger.info('No new tweet media.')
            return
        logger.info(f'Target tweet media count={len(target_tweet_ids)}')

        if self._save_mode == 'google':
            self.google_photos.set_album_id()

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
                    logger.warning(f'Save failed. tweet_id={tweet_id}, media_url={url}')
                    continue

            # store update
            try:
                self.store.insert_tweet_info(tweet_id, target_tweet.user.screen_name, str(target_tweet.created_at))
            except Exception as e:
                logger.exception(f'Insert failed. tweet_id={tweet_id}, exception={e.args}')

            if not failed_upload_medias:
                logger.debug(f'All media upload succeeded. urls={target_tweet_media.urls}')
                continue

            # store failed upload media
            for failed_url, description in failed_upload_medias:
                try:
                    self.store.insert_failed_upload_media(failed_url, description, target_tweet.user.screen_name)
                except Exception as e:
                    logger.exception(f'Insert failed. failed_url={failed_url}, description={description},'
                                     f'exception={e.args}')

    def retry_backup_media(self) -> None:
        url: str = ''
        try:
            for url, description, user_id in self.store.fetch_all_failed_upload_medias():
                logger.info(f'Retry Save media. media_url={url}')
                is_saved: bool = self.save_media(url, description, user_id)
                if not is_saved:
                    logger.warning(f'Retry Save failed. media_url={url}')
                    continue
                self.store.delete_failed_upload_media(url)
        except Exception as e:
            logger.exception(f'Retry backup failed. failed_url={url}, exception={e.args}')

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
                    logger.info(f'Crawling start. user = {user.id}, mode={self.twitter.mode}')
                    self.crawling_tweets(user)
            except Exception as e:
                logger.exception(f'Crawling error exception={e.args}')

            logger.info(f'Interval. sleep {interval_minutes} minutes.')
            time.sleep(interval_minutes * 60)


if __name__ == '__main__':
    Log.init_logger(log_name='crawler')
    logger: logging.Logger = logging.getLogger(__name__)
    crawler = Crawler()
    crawler.main()

logger = logging.getLogger(__name__)
