create table uploaded_media_tweet
(
    tweet_id   text not null
        constraint uploaded_media_tweet_pk
            primary key,
    user_id    text not null,
    add_date   text not null,
    tweet_date text not null
);

create table failed_upload_media
(
    url         text not null
        constraint failed_upload_media_pk
            primary key,
    description text not null,
    user_id     text not null
);
