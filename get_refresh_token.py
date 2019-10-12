#!/usr/bin/python3

from typing import List

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

from app.env import Env

SCOPES: List[str] = ['https://www.googleapis.com/auth/photoslibrary']


def main() -> None:
    client_id: str = Env.get_environment('GOOGLE_CLIENT_ID', required=True)
    client_secret: str = Env.get_environment('GOOGLE_CLIENT_SECRET', required=True)
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
    credentials: Credentials = flow.run_console()
    print(f'refresh_token: {vars(credentials)["_refresh_token"]}')


if __name__ == '__main__':
    main()
