-- cp2 physical model, sqlite 3nf

PRAGMA foreign_keys = ON;

-- platform
CREATE TABLE IF NOT EXISTS platform (
    platform_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    description   TEXT
);

-- telegram channels
CREATE TABLE IF NOT EXISTS channel (
    channel_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id         INTEGER NOT NULL REFERENCES platform(platform_id),
    channel_name        TEXT    NOT NULL,
    channel_username    TEXT    NOT NULL UNIQUE,
    channel_subscribers INTEGER,
    source_type         TEXT,
    UNIQUE(channel_username)
);

CREATE INDEX IF NOT EXISTS idx_channel_platform ON channel(platform_id);

-- twitter authors
CREATE TABLE IF NOT EXISTS twitter_user (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name       TEXT    NOT NULL UNIQUE,
    user_followers  INTEGER DEFAULT 0,
    user_verified   INTEGER DEFAULT 0
);

-- posts (tg + twitter)
CREATE TABLE IF NOT EXISTS post (
    post_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id     INTEGER NOT NULL REFERENCES platform(platform_id),
    channel_id      INTEGER REFERENCES channel(channel_id),
    user_id         INTEGER REFERENCES twitter_user(user_id),
    original_id     TEXT,
    date            TEXT    NOT NULL,
    text            TEXT,
    views           INTEGER DEFAULT 0,
    word_count      INTEGER DEFAULT 0,
    has_media       INTEGER DEFAULT 0,
    has_url         INTEGER DEFAULT 0,
    is_retweet      INTEGER DEFAULT 0,
    collection_date TEXT
);

CREATE INDEX IF NOT EXISTS idx_post_platform   ON post(platform_id);
CREATE INDEX IF NOT EXISTS idx_post_channel    ON post(channel_id);
CREATE INDEX IF NOT EXISTS idx_post_user       ON post(user_id);
CREATE INDEX IF NOT EXISTS idx_post_date       ON post(date);

-- likes/forwards/etc
CREATE TABLE IF NOT EXISTS engagement (
    engagement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL UNIQUE REFERENCES post(post_id),
    likes           INTEGER DEFAULT 0,
    retweets        INTEGER DEFAULT 0,
    forwards        INTEGER DEFAULT 0,
    replies         INTEGER DEFAULT 0,
    reactions       INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_engagement_post ON engagement(post_id);

-- vader score
CREATE TABLE IF NOT EXISTS sentiment (
    sentiment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL UNIQUE REFERENCES post(post_id),
    score           REAL,
    label           TEXT
);

CREATE INDEX IF NOT EXISTS idx_sentiment_post  ON sentiment(post_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment(label);

-- leaders + hotspots
CREATE TABLE IF NOT EXISTS named_entity (
    entity_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    entity_type TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_type ON named_entity(entity_type);

CREATE TABLE IF NOT EXISTS post_entity (
    post_id     INTEGER NOT NULL REFERENCES post(post_id),
    entity_id   INTEGER NOT NULL REFERENCES named_entity(entity_id),
    PRIMARY KEY (post_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_post_entity_entity ON post_entity(entity_id);

CREATE TABLE IF NOT EXISTS hashtag (
    hashtag_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS post_hashtag (
    post_id     INTEGER NOT NULL REFERENCES post(post_id),
    hashtag_id  INTEGER NOT NULL REFERENCES hashtag(hashtag_id),
    PRIMARY KEY (post_id, hashtag_id)
);

CREATE INDEX IF NOT EXISTS idx_post_hashtag_tag ON post_hashtag(hashtag_id);

INSERT OR IGNORE INTO platform (name, description) VALUES
    ('telegram', 'Telegram messaging platform — channels and groups'),
    ('twitter',  'Twitter/X microblogging platform');
