# load clean csvs into sqlite (cp2)

import sqlite3
import csv
import re
import shutil
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
CP1_CLEAN   = BASE_DIR / "capstone1" / "data" / "clean"
CP2_DIR     = BASE_DIR / "capstone2"
DB_PATH     = CP2_DIR / "data" / "politrace.db"
SCHEMA_PATH = CP2_DIR / "schema" / "create_tables.sql"
TMP_DB      = Path("/tmp/politrace_build.db")

TELEGRAM_CSV = CP1_CLEAN / "telegram_raw_clean.csv"
TWITTER_CSV  = CP1_CLEAN / "twitter_raw_clean.csv"


def parse_list(value):
    if not value or str(value).strip() in ("", "nan", "None"):
        return []
    items = [x.strip().strip('"').strip("'") for x in str(value).split(",")]
    return [x for x in items if x]


def parse_hashtags(value):
    if not value or str(value).strip() in ("", "nan", "None"):
        return []
    tags = re.split(r"[,\s]+", str(value))
    tags = [t.lstrip("#").lower().strip() for t in tags]
    return [t for t in tags if t]


def to_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def to_float(value, default=None):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def to_bool(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("true", "1", "yes") else 0
    return int(bool(value))


def connect():
    if TMP_DB.exists():
        TMP_DB.unlink()
    conn = sqlite3.connect(str(TMP_DB))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = OFF")
    return conn


def apply_schema(conn, schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    print("Schema applied")


entity_cache = {}
hashtag_cache = {}


def get_or_create_entity(cur, name, entity_type):
    key = name.lower()
    if key not in entity_cache:
        cur.execute(
            "INSERT OR IGNORE INTO named_entity (name, entity_type) VALUES (?, ?)",
            (name, entity_type),
        )
        cur.execute("SELECT entity_id FROM named_entity WHERE name = ?", (name,))
        entity_cache[key] = cur.fetchone()[0]
    return entity_cache[key]


def get_or_create_hashtag(cur, tag):
    tag = tag.lower()
    if tag not in hashtag_cache:
        cur.execute("INSERT OR IGNORE INTO hashtag (tag) VALUES (?)", (tag,))
        cur.execute("SELECT hashtag_id FROM hashtag WHERE tag = ?", (tag,))
        hashtag_cache[tag] = cur.fetchone()[0]
    return hashtag_cache[tag]


def load_telegram(conn):
    print("Loading Telegram data...")
    cur = conn.cursor()
    cur.execute("SELECT platform_id FROM platform WHERE name = 'telegram'")
    platform_id = cur.fetchone()[0]
    channel_cache = {}
    count = 0

    with open(TELEGRAM_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get("channel_username", "").strip() or "unknown"

            if username not in channel_cache:
                cur.execute(
                    "INSERT OR IGNORE INTO channel "
                    "(platform_id, channel_name, channel_username, channel_subscribers, source_type) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (platform_id, row.get("channel_name", "").strip(), username,
                     to_int(row.get("channel_subscribers")),
                     row.get("source_type", "").strip()),
                )
                cur.execute("SELECT channel_id FROM channel WHERE channel_username = ?", (username,))
                channel_cache[username] = cur.fetchone()[0]

            channel_id = channel_cache[username]

            cur.execute(
                "INSERT INTO post "
                "(platform_id, channel_id, user_id, original_id, date, text, "
                "views, word_count, has_media, has_url, is_retweet, collection_date) "
                "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (platform_id, channel_id,
                 str(row.get("message_id", "")).strip(),
                 row.get("date", "").strip(),
                 row.get("text", "").strip(),
                 to_int(row.get("views")),
                 to_int(row.get("word_count")),
                 to_bool(row.get("has_media", "False")),
                 to_bool(row.get("has_url", "False")),
                 row.get("collection_date", "").strip()),
            )
            post_id = cur.lastrowid

            cur.execute(
                "INSERT INTO engagement (post_id, likes, retweets, forwards, replies, reactions) "
                "VALUES (?, 0, 0, ?, ?, ?)",
                (post_id, to_int(row.get("forwards")),
                 to_int(row.get("replies_count")),
                 to_int(row.get("reactions_count"))),
            )

            score = to_float(row.get("sentiment_score"))
            label = row.get("sentiment_label", "").strip()
            if score is not None or label:
                cur.execute(
                    "INSERT INTO sentiment (post_id, score, label) VALUES (?, ?, ?)",
                    (post_id, score, label),
                )

            for leader in parse_list(row.get("mentioned_leaders", "")):
                eid = get_or_create_entity(cur, leader, "leader")
                cur.execute("INSERT OR IGNORE INTO post_entity (post_id, entity_id) VALUES (?, ?)", (post_id, eid))
            for hotspot in parse_list(row.get("mentioned_hotspots", "")):
                eid = get_or_create_entity(cur, hotspot, "hotspot")
                cur.execute("INSERT OR IGNORE INTO post_entity (post_id, entity_id) VALUES (?, ?)", (post_id, eid))

            count += 1
            if count % 10000 == 0:
                conn.commit()
                print(f"  Telegram: {count:,} rows...")

    conn.commit()
    print(f"Telegram done: {count:,} posts")


def load_twitter(conn):
    print("Loading Twitter data...")
    cur = conn.cursor()
    cur.execute("SELECT platform_id FROM platform WHERE name = 'twitter'")
    platform_id = cur.fetchone()[0]
    user_cache = {}
    count = 0

    with open(TWITTER_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_name = row.get("user_name", "").strip() or "unknown"

            if user_name not in user_cache:
                cur.execute(
                    "INSERT OR IGNORE INTO twitter_user (user_name, user_followers, user_verified) "
                    "VALUES (?, ?, ?)",
                    (user_name, to_int(row.get("user_followers")),
                     to_bool(row.get("user_verified", "False"))),
                )
                cur.execute("SELECT user_id FROM twitter_user WHERE user_name = ?", (user_name,))
                user_cache[user_name] = cur.fetchone()[0]

            user_id = user_cache[user_name]

            cur.execute(
                "INSERT INTO post "
                "(platform_id, channel_id, user_id, original_id, date, text, "
                "views, word_count, has_media, has_url, is_retweet, collection_date) "
                "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)",
                (platform_id, user_id,
                 str(row.get("tweet_id", "")).strip(),
                 row.get("date", "").strip(),
                 row.get("text", "").strip(),
                 to_int(row.get("views")),
                 to_int(row.get("word_count")),
                 to_bool(row.get("is_retweet", "False")),
                 row.get("collection_date", "").strip()),
            )
            post_id = cur.lastrowid

            cur.execute(
                "INSERT INTO engagement (post_id, likes, retweets, forwards, replies, reactions) "
                "VALUES (?, ?, ?, 0, ?, 0)",
                (post_id, to_int(row.get("likes")),
                 to_int(row.get("retweets")),
                 to_int(row.get("replies"))),
            )

            score = to_float(row.get("sentiment_score"))
            label = row.get("sentiment_label", "").strip()
            if score is not None or label:
                cur.execute(
                    "INSERT INTO sentiment (post_id, score, label) VALUES (?, ?, ?)",
                    (post_id, score, label),
                )

            for leader in parse_list(row.get("mentioned_leaders", "")):
                eid = get_or_create_entity(cur, leader, "leader")
                cur.execute("INSERT OR IGNORE INTO post_entity (post_id, entity_id) VALUES (?, ?)", (post_id, eid))
            for hotspot in parse_list(row.get("mentioned_hotspots", "")):
                eid = get_or_create_entity(cur, hotspot, "hotspot")
                cur.execute("INSERT OR IGNORE INTO post_entity (post_id, entity_id) VALUES (?, ?)", (post_id, eid))

            for tag in parse_hashtags(row.get("hashtags", "")):
                hid = get_or_create_hashtag(cur, tag)
                cur.execute("INSERT OR IGNORE INTO post_hashtag (post_id, hashtag_id) VALUES (?, ?)", (post_id, hid))

            count += 1
            if count % 10000 == 0:
                conn.commit()
                print(f"  Twitter: {count:,} rows...")

    conn.commit()
    print(f"Twitter done: {count:,} posts")


def main():
    print(f"Building DB at: {TMP_DB}")
    conn = connect()
    apply_schema(conn, SCHEMA_PATH)
    load_telegram(conn)
    load_twitter(conn)

    cur = conn.cursor()
    tables = ["platform", "channel", "twitter_user", "post", "engagement",
              "sentiment", "named_entity", "post_entity", "hashtag", "post_hashtag"]
    print("\nRow counts:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t:20s}: {cur.fetchone()[0]:>10,}")

    conn.close()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(TMP_DB), str(DB_PATH))
    print(f"\nDone! DB saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
