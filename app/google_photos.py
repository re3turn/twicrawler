#!/usr/bin/python3

import os
import sys
import googleapiclient.errors
import requests

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from retry import retry
from googleapiclient.discovery import build
from httplib2 import Http

API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
CLIENT_SECRETS_FILE = 'google_photos_client_secrets.json'
TOKEN_FILE = 'google_photos_token.json'
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
UPLOAD_API_URL ='https://photoslibrary.googleapis.com/v1/uploads'


class GoogleApiResponseNG(Exception):
    pass


class GooglePhotos:
    def __init__(self):
        self.make_client_secret_json()
        self.make_access_token_json()
        self.access_token_store = Storage(TOKEN_FILE)
        self.credentials = self.access_token_store.get()
        self.service = None

    @staticmethod
    def make_client_secret_json():
        project_id = os.environ.get('GOOGLE_PROJECT_ID')
        if project_id is None:
            sys.exit('Please set environment "GOOGLE_PROJECT_ID"')

        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        if client_secret is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_SECRET"')

        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if client_id is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_ID"')

        client_seclet = '{' \
                            '"installed": {' \
                                f'"client_id": "{client_id}",' \
                                f'"project_id": "{project_id}",' \
                                '"auth_uri": "https://accounts.google.com/o/oauth2/auth",' \
                                '"token_uri": "https://oauth2.googleapis.com/token",' \
                                '"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",' \
                                f'"client_secret": "{client_secret}",' \
                                '"redirect_uris": [' \
                                    '"urn:ietf:wg:oauth:2.0:oob",' \
                                    '"http://localhost"' \
                                ']' \
                            '}' \
                        '}'

        with open(CLIENT_SECRETS_FILE, mode='w') as f:
            f.write(client_seclet)

    @staticmethod
    def make_access_token_json():
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if client_id is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_ID"')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        if client_secret is None:
            sys.exit('Please set environment "GOOGLE_CLIENT_SECRET"')
        access_token = os.environ.get('GOOGLE_ACCESS_TOKEN')
        refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        if (not os.path.exists(TOKEN_FILE)) and (access_token is not None) and (refresh_token is not None):
            token = '{' \
                        f'"access_token": "{access_token}",' \
                        f'"client_id": "{client_id}",' \
                        f'"client_secret": "{client_secret}",' \
                        f'"refresh_token": "{refresh_token}",' \
                        '"token_expiry": "2019-01-01T00:00:00Z",' \
                        '"token_uri": "https://oauth2.googleapis.com/token",' \
                        '"user_agent": null,' \
                        '"revoke_uri": "https://oauth2.googleapis.com/revoke",' \
                        '"id_token": null,' \
                        '"id_token_jwt": null,' \
                        '"scopes": [' \
                            '"https://www.googleapis.com/auth/photoslibrary"' \
                        '],' \
                        '"token_info_uri": "https://oauth2.googleapis.com/tokeninfo",' \
                        '"invalid": false,' \
                        '"_class": "OAuth2Credentials",' \
                        '"_module": "oauth2client.client"' \
                    '}'

            with open(TOKEN_FILE, mode='w') as f:
                f.write(token)

    def update_authenticated_service(self):
        needs_update_service = False
        if not self.credentials or self.credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
            self.credentials = tools.run_flow(flow, self.access_token_store)
            needs_update_service = True
        if self.credentials.access_token_expired:
            self.credentials.refresh(Http())
            self.access_token_store.locked_put(self.credentials)
            needs_update_service = True
        if (not self.service) or needs_update_service:
            self.service = build(API_SERVICE_NAME, API_VERSION, http=self.credentials.authorize(Http()))

    @retry(googleapiclient.errors.HttpError, tries=3, delay=1)
    def create_media_item(self, new_item):
        self.update_authenticated_service()
        response = self.service.mediaItems().batchCreate(body=new_item).execute()
        status = response['newMediaItemResults'][0]['status']
        return status

    @retry((requests.exceptions.HTTPError, GoogleApiResponseNG), tries=3, delay=1)
    def _execute_upload_api(self, data, upload_file_name):
        self.update_authenticated_service()
        headers = {
            'Authorization': "Bearer " + self.credentials.access_token,
            'Content-Type': 'application/octet-stream',
            'X-Goog-Upload-File-Name': upload_file_name,
            'X-Goog-Upload-Protocol': "raw",
        }
        response = requests.post(UPLOAD_API_URL, data=data, headers=headers)
        if not response.ok:
            raise GoogleApiResponseNG(f'Google API response NG, content={response.content}')
        return response

    def upload_media(self, file_path):
        with open(file_path, 'rb') as file_data:
            response = self._execute_upload_api(data=file_data, upload_file_name=os.path.basename(file_path))

        upload_token = response.content.decode('utf-8')
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
