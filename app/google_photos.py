#!/usr/bin/python3

import logging
import os
import googleapiclient.errors

from typing import Dict, List, Union
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
        self._album_title: str = Env.get_environment('GOOGLE_ALBUM_TITLE', default='')
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
    def _create_media_item(self, upload_token: str, description: str) -> Dict[str, str]:
        logger.debug('Create new item for Google Photos')
        new_item: dict = {
            'newMediaItems': [{
                'description': description,
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }

        if self._album_title != '':
            new_item.update({
                'albumId': self._album_id,
                'albumPosition': {
                    'position': 'FIRST_IN_ALBUM',
                }})
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
            raise GoogleApiResponseNG(msg)
        return upload_token.decode('utf-8')

    def upload_media(self, file_path: str, description: str) -> Dict[str, str]:
        logger.info(f'Upload media to Google Photos. path={file_path}')
        upload_token: str = self._execute_upload_api(file_path=file_path)

        return self._create_media_item(upload_token, description)

    def init_album(self) -> None:
        if self._album_title == '':
            return
        self._album_id = self._fetch_album_id()
        if self._album_id == '':
            self._create_new_album()

    def _fetch_album_id(self) -> str:
        page_token = ''
        while True:
            api_result: dict = self._fetch_albums(page_token)
            if 'albums' in api_result:
                for album in api_result['albums']:
                    if album['title'] == self._album_title:
                        return album['id']
            if 'nextPageToken' in api_result:
                page_token = api_result['nextPageToken']
                continue

            return ''

    def _fetch_albums(self, page_token: str) -> dict:
        logger.debug(f'Execute "service.albums().list()" to fetch albums list in Google Photos.')
        params: Dict[str, Union[int, str, bool]] = {
            'pageSize': 50,
            'pageToken': page_token,
            'excludeNonAppCreatedData': True
        }
        return self.service.albums().list(**params).execute(num_retries=3)

    def _create_new_album(self) -> None:
        logger.debug(f'Execute "service.albums().create()" to create new album to Google Photos. '
                     f'album_title={self._album_title}')
        params: Dict[str, Dict[str, str]] = {
            'album': {
                'title': self._album_title
            }
        }
        api_result: dict = self.service.albums().create(body=params).execute(num_retries=3)
        self._album_id = api_result['id']


logger: logging.Logger = logging.getLogger(__name__)

if __name__ == '__main__':
    Log.init_logger(log_name='google_photos')
    logger = logging.getLogger(__name__)
    google_photo = GooglePhotos()
    print(google_photo.upload_media('test.jpg', 'test'))
