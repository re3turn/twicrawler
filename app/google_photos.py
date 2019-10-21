#!/usr/bin/python3

import logging
import os
import googleapiclient.errors

from typing import Dict, List, Union, Any
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
ALBUMS_API_URL = 'https://photoslibrary.googleapis.com/v1/albums'
DUMMY_ACCESS_TOKEN = 'dummy_access_token'


class GoogleApiResponseNG(Exception):
    pass


class GooglePhotos:
    def __init__(self) -> None:
        self.credentials = self.make_credentials()
        self.service = build(API_SERVICE_NAME, API_VERSION, credentials=self.credentials, cache_discovery=False)
        self.authorized_http = AuthorizedHttp(credentials=self.credentials)
        self._albume_title: str = Env.get_environment('GOOGLE_ALBUM_TITLE', default='')
        self._album_id: str = ''

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
        logger.debug(f'Execute "POST:{UPLOAD_API_URL}" to upload media to Google Photos. path={file_path}')
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
            msg: str = f'"POST:{UPLOAD_API_URL}" response NG, status={response.status}, content={upload_token}'
            logger.debug(msg)
            raise GoogleApiResponseNG(msg)
        return upload_token.decode('utf-8')

    def upload_media(self, file_path: str, description: str) -> Dict[str, str]:
        logger.info(f'Upload media to Google Photos. path={file_path}')
        upload_token: str = self._execute_upload_api(file_path=file_path)

        new_item: dict = {
            'newMediaItems': [{
                'description': description,
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }

        if self._albume_title != '':
            new_item.update({
                'albumId': self._album_id,
                'albumPosition': {
                    'position': 'FIRST_IN_ALBUM',
                }})
        return self.create_media_item(new_item)

    def init_album(self) -> None:
        if self._albume_title == '':
            return

        self._album_id = self._get_album_id()
        if self._album_id == '':
            logger.info(f'Create new album "{self._albume_title}" to Google Photos.')
            self._execute_create_new_album_api()

    def _get_album_id(self) -> str:
        params: Dict[str, Union[int, str, bool]] = {
                'pageSize': 50,
                'pageToken': '',
                'excludeNonAppCreatedData': True
            }
        while True:
            api_result: dict = self._execute_get_albums_api(params)
            if 'albums' in api_result:
                for album in api_result['albums']:
                    if album['title'] == self._albume_title:
                        return album['id']
            if 'nextPageToken' in api_result:
                params['pageToken'] = api_result['nextPageToken']
                continue
            break

        return ''

    def _execute_get_albums_api(self, params: Dict[str, Union[int, str, bool]]) -> dict:
        logger.debug(f'Execute "service.albums().list()" to get albums list in Google Photos.')
        return self.service.albums().list(**params).execute(num_retries=3)

    def _execute_create_new_album_api(self) -> None:
        logger.debug(f'Execute "service.albums().create()" to create new album to Google Photos. \
            album_title={self._albume_title}')
        params: Dict[str, Dict[str, str]] = {
            'album': {
                'title': self._albume_title
            }
        }
        api_result: dict =  self.service.albums().create(body=params).execute(num_retries=3)
        self._album_id = api_result['id']


if __name__ == '__main__':
    Log.init_logger(log_name='google_photos')
    logger: logging.Logger = logging.getLogger(__name__)
    google_photo = GooglePhotos()
    print(google_photo.upload_media('test.jpg', 'test'))

logger = logging.getLogger(__name__)
