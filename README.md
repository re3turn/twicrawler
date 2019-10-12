# Installation

## Requirement
 - python3.7.*
 - PostgreSQL
 - Twitter APIs
 - Google APIs

## Install

```:bash
git clone https://github.com/re3turn/twicrawler.git
cd twicrawler
pip3 install -r requirements.txt
```

## Get Google refresh token

Execute `get_refresh_token.py` after setting environment variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

```:bash
$ python3 get_refresh_token.py
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&.....
Enter the authorization code: {AUTHORIZATION CODE}
refresh_token: {REFRESH TOKEN}
```

# Environment variable 

| Environment variable        | Description                                                                                                     | Require |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- | ------- |
| TWITTER_USER_IDS            | Twitter user ID to crawling.If multiple users are specified, separate them with `,`                             | ✓       |
| INTERVAL                    | Crawler interval(minutes). default=`5` minutes                                                                  |         |
| MODE_SPECIFIED              | Specifies Crawler mode. `rt`, `fav`, `mixed`. default=`rt`                                                      |         |
| TWEET_COUNT                 | Specifies the number of tweet statuses to retrieve. default=`200`                                               |         |
| TWEET_PAGES                 | Specifies the page of results to retrieve. default=`25`                                                          |         |
| DATABASE_URL                | Database url. format `postgres://<username>:<password>@<hostname>:<port>/<database>`                            | ✓       |
| DATABASE_SSLMODE            | [Database sslmode.](https://gist.github.com/pfigue/3440e2bc986550a6b8ec#valid-sslmode-values) default=`require` |         |
| TZ                          | Time zone                                                                                                       |         |
| TWITTER_CONSUMER_KEY        | Twitter consumer API keys                                                                                       | ✓       |
| TWITTER_CONSUMER_SECRET     | Twitter consumer API secret key                                                                                 | ✓       |
| TWITTER_ACCESS_TOKEN        | Twitter Access token                                                                                            | ✓       |
| TWITTER_ACCESS_TOKEN_SECRET | Twitter Access token secret                                                                                     | ✓       |
| GOOGLE_CLIENT_ID            | Google API client id                                                                                            | ✓       |
| GOOGLE_CLIENT_SECRET        | Google API client secret                                                                                        | ✓       |
| GOOGLE_REFRESH_TOKEN        | Google API refresh token                                                                                        | ✓       |
