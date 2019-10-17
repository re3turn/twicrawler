#!/usr/bin/python3

import logging
import os
import googleapiclient.errors

from typing import Dict, List
from retry import retry
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp

from app.env import Env
from app.log import Log

API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
SCOPES: List[str] = ['https://www.googleapis.com/auth/photoslibrary']
UPLOAD_API_URL = 'https://photoslibrary.googleapis.com/v1/uploads'
DUMMY_ACCESS_TOKEN = 'dummy_access_token'


class GoogleApiResponseNG(Exception):
    pass


class GooglePhotos:
    def __init__(self) -> None:
        self.credentials = self.make_credentials()
        self.service = build(API_SERVICE_NAME, API_VERSION, credentials=self.credentials, cache_discovery=False)
        self.authorized_http = AuthorizedHttp(credentials=self.credentials)

    @staticmethod
    def make_credentials() -> Credentials:
        client_id: str = Env.get_environment('GOOGLE_CLIENT_ID', required=True)
        client_secret: str = Env.get_environment('GOOGLE_CLIENT_SECRET', required=True)
        refresh_token: str = Env.get_environment('GOOGLE_REFRESH_TOKEN', required=True)
        return Credentials(
            token=DUMMY_ACCESS_TOKEN,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

    @retry(googleapiclient.errors.HttpError, tries=3, delay=2, backoff=2)
    def create_media_item(self, new_item: dict) -> Dict[str, str]:
        logger.debug('Create new item for Google Photos')
        response: dict = self.service.mediaItems().batchCreate(body=new_item).execute()
        status: Dict[str, str] = response['newMediaItemResults'][0]['status']
        return status

    @retry((GoogleApiResponseNG, ConnectionError, TimeoutError), tries=3, delay=2, backoff=2)
    def _execute_upload_api(self, file_path: str) -> str:
        logger.debug(f'Execute API to upload media to Google Photos. path={file_path}')
        with open(file_path, 'rb') as file_data:
            headers = {
                'Authorization': 'Bearer ' + self.credentials.token,
                'Content-Type': 'application/octet-stream',
                'X-Goog-Upload-File-Name': os.path.basename(file_path),
                'X-Goog-Upload-Protocol': 'raw',
            }
            (response, upload_token) = self.authorized_http.request(uri=UPLOAD_API_URL, method='POST', body=file_data,
                                                                    headers=headers)

        if response.status != 200:
            logger.debug(f'Google API response NG, status={response.status}, content={upload_token}')
            raise GoogleApiResponseNG(f'Google API response NG, status={response.status}, content={upload_token}')
        return upload_token.decode('utf-8')

    def upload_media(self, file_path: str, description: str) -> Dict[str, str]:
        logger.info(f'Upload media to Google Photos. path={file_path}')
        upload_token: str = self._execute_upload_api(file_path=file_path)

        new_item = {
            'newMediaItems': [{
                'description': description,
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }

        return self.create_media_item(new_item)


if __name__ == '__main__':
    Log.init_logger(log_name='google_photos')
    logger: logging.Logger = logging.getLogger(__name__)
    google_photo = GooglePhotos()
    print(google_photo.upload_media('test.jpg', 'test'))

logger = logging.getLogger(__name__)
