#!/usr/bin/python3

import os
import sys
import googleapiclient.errors

from retry import retry
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp

API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
UPLOAD_API_URL ='https://photoslibrary.googleapis.com/v1/uploads'


class GoogleApiResponseNG(Exception):
    pass


class GooglePhotos:
    def __init__(self):
        self.credentials = self.make_credentials()
        self.service = build(API_SERVICE_NAME, API_VERSION, credentials=self.credentials)
        self.authorized_http = AuthorizedHttp(credentials=self.credentials)

    @staticmethod
    def make_credentials():
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if client_id is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_ID"')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        if client_secret is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_SECRET"')
        access_token = os.environ.get('GOOGLE_ACCESS_TOKEN')
        refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        return Credentials(
            access_token,
            refresh_token,
            None,
            "https://oauth2.googleapis.com/token",
            client_id,
            client_secret,
            SCOPES
        )

    @retry(googleapiclient.errors.HttpError, tries=3, delay=1)
    def create_media_item(self, new_item):
        response = self.service.mediaItems().batchCreate(body=new_item).execute()
        status = response['newMediaItemResults'][0]['status']
        return status

    @retry(GoogleApiResponseNG, tries=3, delay=1)
    def _execute_upload_api(self, data, upload_file_name):
        headers = {
            'Authorization': "Bearer " + self.credentials.token,
            'Content-Type': 'application/octet-stream',
            'X-Goog-Upload-File-Name': upload_file_name,
            'X-Goog-Upload-Protocol': "raw",
        }
        (response, upload_token) = self.authorized_http.request(uri=UPLOAD_API_URL, method='POST', body=data, headers=headers)
        if response.status != 200:
            raise GoogleApiResponseNG(f'Google API response NG, content={upload_token}')
        return upload_token.decode("utf-8")

    def upload_media(self, file_path):
        with open(file_path, 'rb') as file_data:
            upload_token = self._execute_upload_api(data=file_data, upload_file_name=os.path.basename(file_path))

        new_item = {
            'newMediaItems': [{
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }

        return self.create_media_item(new_item)


if __name__ == '__main__':
    google_photo = GooglePhotos()
    print(google_photo.upload_media("test.jpg"))
