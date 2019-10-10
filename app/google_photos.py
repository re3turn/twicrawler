#!/usr/bin/python3

import os
import googleapiclient.errors

from typing import IO
from retry import retry
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow

from app.env import Env

API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
UPLOAD_API_URL = 'https://photoslibrary.googleapis.com/v1/uploads'
DUMMY_ACCESS_TOKEN = 'dummy_access_token'


class GoogleApiResponseNG(Exception):
    pass


class GooglePhotos:
    def __init__(self):
        self.credentials = self.make_credentials()
        self.service = build(API_SERVICE_NAME, API_VERSION, credentials=self.credentials)
        self.authorized_http = AuthorizedHttp(credentials=self.credentials)

    @staticmethod
    def get_access_token():
        client_id = Env.get_environment('GOOGLE_CLIENT_ID', required=True)
        client_secret = Env.get_environment('GOOGLE_CLIENT_SECRET', required=True)
        client_config = {
            'installed': {
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://accounts.google.com/o/oauth2/token',
                'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob'],
                'client_id': client_id,
                'client_secret': client_secret
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_console()
        print(f'refresh_token: {vars(credentials)["_refresh_token"]}')

    @staticmethod
    def make_credentials() -> Credentials:
        client_id = Env.get_environment('GOOGLE_CLIENT_ID', required=True)
        client_secret = Env.get_environment('GOOGLE_CLIENT_SECRET', required=True)
        refresh_token = Env.get_environment('GOOGLE_REFRESH_TOKEN', required=True)
        return Credentials(
            DUMMY_ACCESS_TOKEN,
            refresh_token,
            None,
            'https://oauth2.googleapis.com/token',
            client_id,
            client_secret,
            SCOPES
        )

    @retry(googleapiclient.errors.HttpError, tries=3, delay=2, backoff=2)
    def create_media_item(self, new_item: dict) -> dict:
        response = self.service.mediaItems().batchCreate(body=new_item).execute()
        status = response['newMediaItemResults'][0]['status']
        return status

    @retry((GoogleApiResponseNG, ConnectionAbortedError, TimeoutError), tries=3, delay=2, backoff=2)
    def _execute_upload_api(self, file_path: str) -> str:
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
            raise GoogleApiResponseNG(f'Google API response NG, status={response.status}, content={upload_token}')
        return upload_token.decode('utf-8')

    def upload_media(self, file_path, description):
        upload_token = self._execute_upload_api(file_path=file_path)

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
    google_photo = GooglePhotos()
    print(google_photo.upload_media('test.jpg', 'test'))
