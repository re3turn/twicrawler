import googleapiclient.errors
import logging

import httplib2
import nose2.tools
import os

from google.oauth2.credentials import Credentials
from httplib2 import Response
from testfixtures import LogCapture
from typing import Any, Tuple, Dict, Union
from unittest import mock

from app.google_photos import GooglePhotos, GoogleApiResponseNG
from tests.lib.utils import load_json, delete_env

JSON_DIR = f'{os.path.dirname(__file__)}/json'
STATIC_CONTENT_DIR = f'{os.path.dirname(__file__)}/static_content'
TEST_UPLOAD_TOKEN = 'test_upload_token'
TEST_DESCRIPTION = 'test_description'
TEST_ALBUM_ID = 'testAlbumId'
TEST_ALBUM_TITLE = 'test_album_title'
TEST_NEXT_PAGE_TOKEN = 'test_next_page_token'

mock_service = mock.MagicMock()
mock_auth = mock.MagicMock()
mock_sleep = mock.MagicMock()


class MockGoogleapiclient:
    class ExecuteApi:
        json_name: str
        func_name: str

        @classmethod
        def execute(cls) -> dict:
            json_path = f'{JSON_DIR}/google_photos/{cls.func_name}/{cls.json_name}.json'
            response_data: dict = load_json(json_path)
            return response_data

    class ExecuteFetchAlbumsApi(ExecuteApi):
        next_page: int = 1

        @classmethod
        def execute(cls, num_retries: int = 0) -> dict:
            json_path = f'{JSON_DIR}/google_photos/{cls.func_name}/{cls.json_name}.json'
            response_data: dict = load_json(json_path)
            if 'nextPageToken' in response_data:
                cls.json_name = f'{cls.json_name}{cls.next_page}'
                cls.next_page += 1
            return response_data

    class UploadApi:
        json_name: str
        func_name: str

        @classmethod
        def request(cls) -> Tuple[Any, bytes]:
            json_path = f'{JSON_DIR}/google_photos/{cls.func_name}/{cls.json_name}.json'
            response: Response = Response(load_json(json_path))
            upload_token: bytes = 'test123456'.encode('utf-8')
            return response, upload_token


class TestGooglePhotos:
    google_photos: GooglePhotos

    @mock.patch('app.google_photos.AuthorizedHttp', mock_auth)
    @mock.patch('app.google_photos.build', mock_service)
    def setUp(self) -> None:
        os.environ['GOOGLE_CLIENT_ID'] = 'DUMMY'
        os.environ['GOOGLE_CLIENT_SECRET'] = 'DUMMY'
        os.environ['GOOGLE_REFRESH_TOKEN'] = 'DUMMY'

        mock_service.reset_mock()
        mock_auth.reset_mock()
        self.google_photos = GooglePhotos()

    @staticmethod
    def tearDown() -> None:
        delete_env('GOOGLE_CLIENT_ID')
        delete_env('GOOGLE_CLIENT_SECRET')
        delete_env('GOOGLE_REFRESH_TOKEN')

    def test_make_credentials(self) -> None:
        credentials: Credentials = self.google_photos.make_credentials()
        assert isinstance(credentials, Credentials)
        assert credentials.client_id == 'DUMMY'
        assert credentials.client_secret == 'DUMMY'
        assert credentials.refresh_token == 'DUMMY'
        assert credentials.token == 'dummy_access_token'
        assert credentials.token_uri == 'https://oauth2.googleapis.com/token'

    @nose2.tools.params(
        'Success',
        'OK',
    )
    def test_create_media_item(self, json_name: str) -> None:
        MockGoogleapiclient.ExecuteApi.json_name = json_name
        MockGoogleapiclient.ExecuteApi.func_name = 'mediaitems_bachcreate_execute'
        config: dict = {'mediaItems.return_value.batchCreate.return_value.execute.return_value':
                        MockGoogleapiclient.ExecuteApi.execute()}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service
        self.google_photos._album_id = ''
        self.google_photos._album_title = ''

        # noinspection PyProtectedMember
        response_status: dict = self.google_photos._create_media_item(TEST_UPLOAD_TOKEN, TEST_DESCRIPTION)
        msg: str = json_name

        assert isinstance(response_status, dict)
        assert 'message' in response_status and response_status['message'] == msg

        new_item_ans = {
            'newMediaItems': [{
                'description': TEST_DESCRIPTION,
                'simpleMediaItem': {
                    'uploadToken': TEST_UPLOAD_TOKEN
                }
            }]
        }
        (_, kwargs) = mock_service.mediaItems.return_value.batchCreate.call_args
        assert 'body' in kwargs and kwargs['body'] == new_item_ans

    @nose2.tools.params(
        'OK',
    )
    def test_create_media_item__album(self, json_name: str) -> None:
        MockGoogleapiclient.ExecuteApi.json_name = json_name
        MockGoogleapiclient.ExecuteApi.func_name = 'mediaitems_bachcreate_execute'
        config: dict = {'mediaItems.return_value.batchCreate.return_value.execute.return_value':
                        MockGoogleapiclient.ExecuteApi.execute()}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service
        self.google_photos._album_id = TEST_ALBUM_ID
        self.google_photos._album_title = TEST_ALBUM_TITLE

        # noinspection PyProtectedMember
        self.google_photos._create_media_item(TEST_UPLOAD_TOKEN, TEST_DESCRIPTION)

        new_item_ans = {
            'newMediaItems': [{
                'description': TEST_DESCRIPTION,
                'simpleMediaItem': {
                    'uploadToken': TEST_UPLOAD_TOKEN
                }
            }],
            'albumId': TEST_ALBUM_ID,
            'albumPosition': {
                'position': 'FIRST_IN_ALBUM',
            }
        }
        (_, kwargs) = mock_service.mediaItems.return_value.batchCreate.call_args
        assert 'body' in kwargs and kwargs['body'] == new_item_ans

    @mock.patch('time.sleep', mock_sleep)  # for retry
    def test_create_media_item__retry(self) -> None:
        res: dict = {'status': 500, 'reason': 'Server Error'}
        error_response = httplib2.Response(res)
        error_response.reason = 'Server Error'
        config: dict = {'mediaItems.return_value.batchCreate.return_value.execute.side_effect':
                        googleapiclient.errors.HttpError(resp=error_response, content=b"{}")}
        mock_error_service = mock.MagicMock()
        mock_error_service.configure_mock(**config)
        self.google_photos.service = mock_error_service

        with LogCapture(level=logging.WARNING) as log:
            with nose2.tools.such.helper.assertRaises(googleapiclient.errors.HttpError):
                # noinspection PyProtectedMember
                self.google_photos._create_media_item(TEST_UPLOAD_TOKEN, TEST_DESCRIPTION)
            assert len(log.records) == 2
            assert mock_error_service.mediaItems.return_value.batchCreate.return_value.execute.call_count == 3

    @nose2.tools.params(
        'request_200',
    )
    def test_execute_upload_api(self, json_name: str) -> None:
        MockGoogleapiclient.UploadApi.json_name = json_name
        MockGoogleapiclient.UploadApi.func_name = 'upload_api_execute'
        mock_auth.request.return_value = MockGoogleapiclient.UploadApi.request()
        self.google_photos.authorized_http = mock_auth
        file_path = f'{STATIC_CONTENT_DIR}/images/test.png'

        # noinspection PyProtectedMember
        upload_token = self.google_photos._execute_upload_api(file_path)
        assert isinstance(upload_token, str)
        assert len(upload_token) != 0

    @mock.patch('time.sleep', mock_sleep)  # for retry
    @nose2.tools.params(
        ('request_400', 2, 3),
    )
    def test_execute_upload_api__retry(self, json_name: str, log_count: int, retry_count: int) -> None:
        MockGoogleapiclient.UploadApi.json_name = json_name
        MockGoogleapiclient.UploadApi.func_name = 'upload_api_execute'
        mock_auth.request.return_value = MockGoogleapiclient.UploadApi.request()
        self.google_photos.authorized_http = mock_auth
        file_path = f'{STATIC_CONTENT_DIR}/images/test.png'

        with LogCapture(level=logging.WARNING) as log:
            with nose2.tools.such.helper.assertRaises(GoogleApiResponseNG):
                # noinspection PyProtectedMember
                self.google_photos._execute_upload_api(file_path)

                # Other than HTTP 200 status
                # WARNING:retry.api:"POST:https://photoslibrary.googleapis.com/v1/uploads" response NG, status=400,
                # content=b'xxxxxx', retrying in n seconds...
            assert len(log.records) == log_count
            assert mock_auth.request.call_count == retry_count

    @nose2.tools.params(
        'albums',
    )
    def test_fetch_albums(self, json_name: str) -> None:
        MockGoogleapiclient.ExecuteFetchAlbumsApi.next_page = 1
        MockGoogleapiclient.ExecuteFetchAlbumsApi.json_name = json_name
        MockGoogleapiclient.ExecuteFetchAlbumsApi.func_name = 'albums_list_execute'
        config: dict = {'albums.return_value.list.return_value.execute.side_effect':
                        MockGoogleapiclient.ExecuteFetchAlbumsApi.execute}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service

        # noinspection PyProtectedMember
        response: dict = self.google_photos._fetch_albums('')
        assert isinstance(response, dict)
        assert 'albums' in response

        params_ans: Dict[str, Union[int, str, bool]] = {
            'pageSize': 50,
            'pageToken': '',
            'excludeNonAppCreatedData': True
        }
        (_, kwargs) = mock_service.albums.return_value.list.call_args
        assert kwargs == params_ans

    @nose2.tools.params(
        ('albums', 'exist_title', 1),
        ('no_albums', 'test', 1),
        ('next_page', 'exist_next_page', 2),
    )
    def test_fetch_album_id(self, json_name: str, album_title: str, call_count: int) -> None:
        MockGoogleapiclient.ExecuteFetchAlbumsApi.next_page = 1
        MockGoogleapiclient.ExecuteFetchAlbumsApi.json_name = json_name
        MockGoogleapiclient.ExecuteFetchAlbumsApi.func_name = 'albums_list_execute'
        config: dict = {'albums.return_value.list.return_value.execute.side_effect':
                        MockGoogleapiclient.ExecuteFetchAlbumsApi.execute}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service
        self.google_photos._album_title = album_title
        # noinspection PyProtectedMember
        album_id: str = self.google_photos._fetch_album_id()

        assert isinstance(album_id, str)
        if json_name == 'no_albums':
            assert len(album_id) == 0
        else:
            assert len(album_id) != 0
        assert mock_service.albums.return_value.list.return_value.execute.call_count == call_count

        params_ans: Dict[str, Union[int, str, bool]] = {
             'pageSize': 50,
             'pageToken': '',
             'excludeNonAppCreatedData': True
         }
        for i, (_, kwargs) in enumerate(mock_service.albums.return_value.list.call_args_list):
            if i > 0:
                params_ans['pageToken'] = TEST_NEXT_PAGE_TOKEN
            assert kwargs == params_ans

    @nose2.tools.params(
        'success',
    )
    def test_create_new_album(self, json_name: str) -> None:
        MockGoogleapiclient.ExecuteApi.json_name = json_name
        MockGoogleapiclient.ExecuteApi.func_name = 'albums_create_execute'
        config: dict = {'albums.return_value.create.return_value.execute.return_value':
                        MockGoogleapiclient.ExecuteApi.execute()}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service
        self.google_photos._album_title = 'test'

        # noinspection PyProtectedMember
        self.google_photos._create_new_album()

        # noinspection PyProtectedMember
        assert isinstance(self.google_photos._album_id, str) and len(self.google_photos._album_id) != 0

    @nose2.tools.params(
        ('', ''),
        ('exist_title', 'get_album_id'),
        ('no_exist_title', 'create_album_id')
    )
    def test_init_album(self, album_title: str, album_id_ans: str) -> None:
        # _create_new_album()
        MockGoogleapiclient.ExecuteApi.json_name = 'success'
        MockGoogleapiclient.ExecuteApi.func_name = 'albums_create_execute'
        # _fetch_album_id()
        MockGoogleapiclient.ExecuteFetchAlbumsApi.next_page = 1
        MockGoogleapiclient.ExecuteFetchAlbumsApi.json_name = 'albums'
        MockGoogleapiclient.ExecuteFetchAlbumsApi.func_name = 'albums_list_execute'

        config: dict = {'albums.return_value.create.return_value.execute.return_value':
                        MockGoogleapiclient.ExecuteApi.execute(),
                        'albums.return_value.list.return_value.execute.side_effect':
                        MockGoogleapiclient.ExecuteFetchAlbumsApi.execute}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service
        self.google_photos._album_title = album_title
        self.google_photos.init_album()

        # noinspection PyProtectedMember
        album_id: str = self.google_photos._album_id
        if album_id_ans == '':
            assert len(album_id) == 0
        else:
            assert len(album_id) != 0

    @nose2.tools.params(
        (f'{STATIC_CONTENT_DIR}/images/test.png', TEST_DESCRIPTION),
    )
    def test_upload_media(self, file_path: str, description: str) -> None:
        # _create_media_item
        MockGoogleapiclient.ExecuteApi.json_name = 'Success'
        MockGoogleapiclient.ExecuteApi.func_name = 'mediaitems_bachcreate_execute'
        config: dict = {'mediaItems.return_value.batchCreate.return_value.execute.return_value':
                        MockGoogleapiclient.ExecuteApi.execute()}
        mock_service.configure_mock(**config)
        self.google_photos.service = mock_service

        # _execute_upload_api
        MockGoogleapiclient.UploadApi.json_name = 'request_200'
        MockGoogleapiclient.UploadApi.func_name = 'upload_api_execute'
        mock_auth.request.return_value = MockGoogleapiclient.UploadApi.request()
        self.google_photos.authorized_http = mock_auth

        msg = f'Upload media to Google Photos. path={file_path}'
        with LogCapture(level=logging.INFO) as log:
            response_status: dict = self.google_photos.upload_media(file_path, description)
            log.check(('app.google_photos', 'INFO', msg))
        assert isinstance(response_status, dict)
        assert 'message' in response_status and response_status['message'] == 'Success'
