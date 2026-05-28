-- =============================================================
-- Capstone Project 2 — Physical Data Model
-- Database: SQLite
-- Dataset: Political Discourse on Social Media (Telegram + Twitter)
-- Normalization: 3NF
-- =============================================================

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────
-- 1. PLATFORM
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform (
    platform_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,          -- 'telegram', 'twitter'
    description   TEXT
);

-- ─────────────────────────────────────────
-- 2. CHANNEL  (Telegram sources)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS channel (
    channel_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id         INTEGER NOT NULL REFERENCES platform(platform_id),
    channel_name        TEXT    NOT NULL,
    channel_username    TEXT    NOT NULL UNIQUE,
    channel_subscribers INTEGER,
    source_type         TEXT,                       -- 'api_scrape', etc.
    UNIQUE(channel_username)
);

CREATE INDEX IF NOT EXISTS idx_channel_platform ON channel(platform_id);

-- ─────────────────────────────────────────
-- 3. TWITTER_USER
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS twitter_user (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name       TEXT    NOT NULL UNIQUE,
    user_followers  INTEGER DEFAULT 0,
    user_verified   INTEGER DEFAULT 0              -- 0 = False, 1 = True
);

-- ─────────────────────────────────────────
-- 4. POST  (unified table for all platforms)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post (
    post_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id     INTEGER NOT NULL REFERENCES platform(platform_id),
    channel_id      INTEGER REFERENCES channel(channel_id),       -- Telegram only
    user_id         INTEGER REFERENCES twitter_user(user_id),     -- Twitter only
    original_id     TEXT,                           -- message_id / tweet_id from source
    date            TEXT    NOT NULL,               -- ISO-8601 datetime
    text            TEXT,
    views           INTEGER DEFAULT 0,
    word_count      INTEGER DEFAULT 0,
    has_media       INTEGER DEFAULT 0,              -- Telegram: 0/1
    has_url         INTEGER DEFAULT 0,              -- Telegram: 0/1
    is_retweet      INTEGER DEFAULT 0,              -- Twitter: 0/1
    collection_date TEXT
);

CREATE INDEX IF NOT EXISTS idx_post_platform   ON post(platform_id);
CREATE INDEX IF NOT EXISTS idx_post_channel    ON post(channel_id);
CREATE INDEX IF NOT EXISTS idx_post_user       ON post(user_id);
CREATE INDEX IF NOT EXISTS idx_post_date       ON post(date);

-- ─────────────────────────────────────────
-- 5. ENGAGEMENT  (per-post interaction metrics)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS engagement (
    engagement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL UNIQUE REFERENCES post(post_id),
    likes           INTEGER DEFAULT 0,
    retweets        INTEGER DEFAULT 0,              -- Twitter retweets
    forwards        INTEGER DEFAULT 0,              -- Telegram forwards
    replies         INTEGER DEFAULT 0,
    reactions       INTEGER DEFAULT 0               -- Telegram reactions
);

CREATE INDEX IF NOT EXISTS idx_engagement_post ON engagement(post_id);

-- ─────────────────────────────────────────
-- 6. SENTIMENT  (one row per post)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sentiment (
    sentiment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL UNIQUE REFERENCES post(post_id),
    score           REAL,                           -- e.g. -0.78 to 1.0
    label           TEXT                            -- 'positive','negative','neutral'
);

CREATE INDEX IF NOT EXISTS idx_sentiment_post  ON sentiment(post_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment(label);

-- ─────────────────────────────────────────
-- 7. NAMED_ENTITY  (leaders + hotspots)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS named_entity (
    entity_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    entity_type TEXT    NOT NULL                    -- 'leader' | 'hotspot'
);

CREATE INDEX IF NOT EXISTS idx_entity_type ON named_entity(entity_type);

-- ─────────────────────────────────────────
-- 8. POST_ENTITY  (many-to-many: post ↔ named_entity)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_entity (
    post_id     INTEGER NOT NULL REFERENCES post(post_id),
    entity_id   INTEGER NOT NULL REFERENCES named_entity(entity_id),
    PRIMARY KEY (post_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_post_entity_entity ON post_entity(entity_id);

-- ─────────────────────────────────────────
-- 9. HASHTAG
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hashtag (
    hashtag_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT    NOT NULL UNIQUE             -- stored lowercase, no '#'
);

-- ─────────────────────────────────────────
-- 10. POST_HASHTAG  (many-to-many: post ↔ hashtag)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_hashtag (
    post_id     INTEGER NOT NULL REFERENCES post(post_id),
    hashtag_id  INTEGER NOT NULL REFERENCES hashtag(hashtag_id),
    PRIMARY KEY (post_id, hashtag_id)
);

CREATE INDEX IF NOT EXISTS idx_post_hashtag_tag ON post_hashtag(hashtag_id);

-- ─────────────────────────────────────────
-- Seed: platforms
-- ─────────────────────────────────────────
INSERT OR IGNORE INTO platform (name, description) VALUES
    ('telegram', 'Telegram messaging platform — channels and groups'),
    ('twitter',  'Twitter/X microblogging platform');
