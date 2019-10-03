create table uploaded_media_tweet
(
    tweet_id   text not null
        constraint uploaded_media_tweet_pk
            primary key,
    user_id    text not null,
    add_date   text not null,
    tweet_date text not null
);

create unique index uploaded_media_tweet_tweet_id_uindex
    on uploaded_media_tweet (tweet_id);
