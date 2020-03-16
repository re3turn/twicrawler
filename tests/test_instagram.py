import nose2.tools
import os
import re
import requests

from typing import List
from unittest import mock

from app.instagram import Instagram
from tests.lib.utils import load_json

JSON_DIR = f'{os.path.dirname(__file__)}/json'

mock_request_get = mock.MagicMock()


class MockRequests:
    @staticmethod
    def get(url: str) -> object:
        json_path = f'{JSON_DIR}/instagram/url_content/{os.path.basename(url.rstrip("/"))}.json'
        get_data: dict = load_json(json_path)
        response: requests.models.Response = requests.models.Response()
        setattr(response, '_content', get_data['content'])
        return response


@mock.patch('requests.get', mock_request_get)
class TestInstagram:
    @nose2.tools.params(
        ('https://www.instagram.com/p/B0v8aXWg8aG/',),  # has single photos
        ('https://www.instagram.com/p/BcDPlNZhhRC/',),  # has multi photos
        ('https://www.instagram.com/p/B0q8HJ0hiQ9/',),  # has videos
    )
    def test_get_json_data(self, url: str) -> None:
        mock_request_get.return_value = MockRequests.get(url)
        instagram = Instagram(url)
        # noinspection PyProtectedMember
        json_data: dict = instagram._get_json_data()
        assert json_data is not None
        assert isinstance(json_data, dict)

    @nose2.tools.params(
        ('https://www.instagram.com/p/B0v8aXWg8aG/', 1),  # has single photos
        ('https://www.instagram.com/p/BcDPlNZhhRC/', 3),  # has multi photos
        ('https://www.instagram.com/p/B0q8HJ0hiQ9/', 1),  # has videos
    )
    def test_get_media_urls(self, url: str, count: int) -> None:
        mock_request_get.return_value = MockRequests.get(url)
        instagram = Instagram(url)
        media_urls: List[str] = instagram.get_media_urls()
        assert len(media_urls) == count
        pattern = re.compile(r'^https?://([\w-]+\.)+[\w-]+/?([\w\-./?%&=+]*)?$')
        for media_url in media_urls:
            assert isinstance(media_url, str)
            assert pattern.fullmatch(media_url) is not None
