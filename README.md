# Installation

## Requirement
- Docker version 18.06.0+
- docker-compose version 1.22.0+
- Twitter APIs
- Google APIs

## Install

```:bash
git clone https://github.com/re3turn/twicrawler.git
cd twicrawler
```

## Setup

Setting [environment variable](#environment-variable) in the `.env` file.

If you need examples, check the sample [`.env.sample`](.env.sample) in this repository.

### Get Google refresh token

Setting [environment variable](#environment-variable) `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env` file.

```
docker-compose build app
docker run -i --env-file=.env twicrawler python get_refresh_token.py
```

#### Execution example

```:bash
$ docker run -i --env-file=.env twicrawler python get_refresh_token.py
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&.....
Enter the authorization code: {AUTHORIZATION CODE}
refresh_token: {REFRESH TOKEN}
```

## Run

```:bash
docker-compose up -d
```

# Environment variable 

## Common

| Environment variable        | Description                                                                                                     | Require |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- | ------- |
| TWITTER_USER_IDS            | Twitter user ID to crawling.If multiple users are specified, separate them with `,`                             | ✓       |
| INTERVAL                    | Crawler interval(minutes). default=`5` minutes                                                                  |         |
| MODE_SPECIFIED              | Specifies Crawler mode. `rt`, `fav`, `mixed`. default=`rt`                                                      |         |
| TWEET_COUNT                 | Specifies the number of tweet statuses to retrieve. default=`200`                                               |         |
| TWEET_PAGES                 | Specifies the page of results to retrieve. default=`25`                                                          |         |
| SAVE_MODE                   | Specifies save media mode. `local` or `google`. default=`local`                                                 |         |
| LOGGING_LEVEL               | [Logging level.](https://docs.python.org/3/library/logging.html#logging-levels) default=`INFO`                  |         |
| DATABASE_URL                | Database url. format `postgres://<username>:<password>@<hostname>:<port>/<database>`                            | ✓       |
| DATABASE_SSLMODE            | [Database sslmode.](https://gist.github.com/pfigue/3440e2bc986550a6b8ec#valid-sslmode-values) default=`require` |         |
| TZ                          | Time zone                                                                                                       |         |
| TWITTER_CONSUMER_KEY        | Twitter consumer API keys                                                                                       | ✓       |
| TWITTER_CONSUMER_SECRET     | Twitter consumer API secret key                                                                                 | ✓       |
| TWITTER_ACCESS_TOKEN        | Twitter Access token                                                                                            | ✓       |
| TWITTER_ACCESS_TOKEN_SECRET | Twitter Access token secret                                                                                     | ✓       |

## SAVE_MODE = google

| Environment variable        | Description                                                            | Require |
| --------------------------- | ---------------------------------------------------------------------- | ------- |
| GOOGLE_CLIENT_ID            | Google API client id                                                   | ✓       |
| GOOGLE_CLIENT_SECRET        | Google API client secret                                               | ✓       |
| GOOGLE_REFRESH_TOKEN        | Google API refresh token                                               | ✓       |
| GOOGLE_ALBUM_TITLE          | Specifies the album title to add media. default=`''`                   |         |
