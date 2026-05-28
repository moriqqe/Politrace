# Capstone Project 2: Data Modeling
**Course:** Introduction to Data, Knowledge and Ontology  
**Student:** Arseniy  
**Dataset:** Political Discourse on Social Media — Telegram & Twitter  
**DBMS:** SQLite 3  
**Submission format:** Report + SQL Scripts + ERD Description  

---

## Step 1 — Understanding the Dataset

### Dataset Summary

The dataset was collected in Capstone Project 1 and covers political discourse across two social media platforms: **Telegram** and **Twitter/X**. The data spans from January 2026 to May 2026 and focuses on geopolitical topics including armed conflicts, sanctions, international leaders, and hotspot regions.

| Attribute | Telegram | Twitter |
|-----------|----------|---------|
| Total records | 15,000 | 14,607 |
| Date range | Mar 2026 – May 2026 | May 2026 |
| Source channels / users | 4 Telegram channels | Anonymous feed |
| Avg sentiment score | −0.1876 | −0.1956 |
| Attributes per record | 20 | 21 |

**Telegram sources:** Reuters World Channel, BBC News World, The New York Times, Disclose.tv  
**Twitter:** API scrape of geopolitical keyword search results

### Key Attributes

**Telegram:** `message_id`, `channel_name`, `channel_username`, `channel_subscribers`, `date`, `text`, `views`, `forwards`, `replies_count`, `reactions_count`, `has_media`, `has_url`, `platform`, `collection_date`, `sentiment_score`, `sentiment_label`, `word_count`, `mentioned_leaders`, `mentioned_hotspots`, `source_type`

**Twitter:** `tweet_id`, `date`, `text`, `likes`, `retweets`, `replies`, `views`, `user_name`, `user_followers`, `user_verified`, `hashtags`, `is_retweet`, `url`, `platform`, `collection_date`, `sentiment_score`, `sentiment_label`, `word_count`, `mentioned_leaders`, `mentioned_hotspots`, `source_type`

### Database Type Selection: Relational (SQL)

A **relational database** was chosen because:
- The data is highly structured with clear entities and defined relationships
- Many-to-many relationships exist (posts ↔ entities, posts ↔ hashtags) that benefit from junction tables
- Sentiment scores and engagement metrics are numerical and well-suited to SQL aggregation
- The dataset fits comfortably in a single SQLite file with fast JOIN performance at ~30k rows
- SQL enables complex analytical queries across platforms, channels, and time periods

A NoSQL document store would have been appropriate if the schema were more fluid or if the text corpus required full-text indexing at scale, but neither condition applies here.

---

## Step 2 — Conceptual Data Modeling

### Entities and Relationships

The conceptual model identifies **10 core entities**:

| Entity | Description |
|--------|-------------|
| **Platform** | The social media platform (Telegram, Twitter) |
| **Channel** | A Telegram channel or news source with subscriber count |
| **TwitterUser** | A Twitter account with follower/verified status |
| **Post** | A single message, tweet, or article — unified across platforms |
| **Engagement** | Platform-specific interaction metrics per post |
| **Sentiment** | NLP-derived sentiment score and label for each post |
| **NamedEntity** | A political leader or geopolitical hotspot mentioned in the text |
| **PostEntity** | Junction table — links posts to named entities (many-to-many) |
| **Hashtag** | A hashtag tag extracted from Twitter posts |
| **PostHashtag** | Junction table — links posts to hashtags (many-to-many) |

### Relationships

- **Platform → Channel**: one-to-many (one platform hosts many channels)
- **Platform → TwitterUser**: one-to-many (conceptually, each user belongs to Twitter)
- **Platform → Post**: one-to-many (each post belongs to one platform)
- **Channel → Post**: one-to-many (a Telegram channel has many posts)
- **TwitterUser → Post**: one-to-many (a user has many tweets)
- **Post → Engagement**: one-to-one (each post has exactly one engagement record)
- **Post → Sentiment**: one-to-one (each post has exactly one sentiment record)
- **Post ↔ NamedEntity** (via PostEntity): many-to-many (a post may mention multiple leaders/hotspots; a leader may appear in many posts)
- **Post ↔ Hashtag** (via PostHashtag): many-to-many (a tweet may have many hashtags; a hashtag appears in many tweets)

**Why this model fits the case:**  
Political discourse naturally centers on a small set of recurring actors (leaders, regions) that appear across thousands of posts and multiple platforms. Separating entity mentions into a dedicated `NamedEntity` table with a junction `PostEntity` avoids text duplication, enables efficient counting and filtering by entity, and supports cross-platform entity comparison queries without scanning full text fields.

---

## Step 3 — Logical Data Modeling (3NF)

The logical model translates the conceptual ERD into normalized tables. All tables satisfy **Third Normal Form (3NF)**:
- Every non-key attribute depends on the whole primary key (2NF)
- No transitive dependencies exist (3NF)

### Normalization Decisions

**Engagement separated from Post:** Metrics like `likes`, `retweets`, `forwards`, `replies`, and `reactions` are functionally dependent only on `post_id` but differ in meaning between platforms (Telegram has forwards/reactions; Twitter has likes/retweets). Placing them in a dedicated `engagement` table removes platform-conditional nulls from `post` and keeps the post table clean.

**Sentiment separated from Post:** `sentiment_label` is functionally dependent on `sentiment_score` (negative score → negative label), which would create a transitive dependency in `post`. Extracting `sentiment` into its own table with `post_id` as the FK eliminates this.

**NamedEntity normalized:** `mentioned_leaders` and `mentioned_hotspots` were stored as comma-separated strings in the CSV — a clear 1NF violation. The logical model atomizes these into individual `named_entity` rows with a junction `post_entity` table.

**Channel and TwitterUser separated:** Though both represent "sources," their attribute sets are entirely disjoint (Telegram: `channel_username`, `channel_subscribers`; Twitter: `user_followers`, `user_verified`). Forcing them into one table would require many NULLs.

### Logical Schema

```
platform (platform_id PK, name UNIQUE, description)

channel (channel_id PK, platform_id FK, channel_name,
         channel_username UNIQUE, channel_subscribers, source_type)

twitter_user (user_id PK, user_name UNIQUE, user_followers, user_verified)

post (post_id PK, platform_id FK, channel_id FK NULL,
      user_id FK NULL, original_id, date NOT NULL, text,
      views, word_count, has_media, has_url, is_retweet, collection_date)

engagement (engagement_id PK, post_id FK UNIQUE,
            likes, retweets, forwards, replies, reactions)

sentiment (sentiment_id PK, post_id FK UNIQUE, score REAL, label TEXT)

named_entity (entity_id PK, name UNIQUE, entity_type)
    -- entity_type: 'leader' | 'hotspot'

post_entity (post_id FK, entity_id FK,  PRIMARY KEY(post_id, entity_id))

hashtag (hashtag_id PK, tag UNIQUE)

post_hashtag (post_id FK, hashtag_id FK, PRIMARY KEY(post_id, hashtag_id))
```

---

## Step 4 — Physical Data Modeling & Database Schema

**DBMS selected: SQLite 3**  
Chosen for its zero-configuration setup, file-based portability, and strong Python support via the built-in `sqlite3` module. Sufficient for the dataset size (~30k rows) and enables all required SQL features including CTEs and window functions.

### SQL Schema (see `schema/create_tables.sql`)

Key implementation decisions:
- `PRAGMA foreign_keys = ON` to enforce referential integrity
- `AUTOINCREMENT` surrogate PKs on all main tables for stable row identification
- `UNIQUE` constraints on natural keys (`channel_username`, `tag`, `name`) to prevent duplicates
- Indexes on all FK columns and frequently filtered columns (`sentiment.label`, `named_entity.entity_type`, `post.date`)
- `NULL` permitted on `post.channel_id` and `post.user_id` (mutually exclusive by platform)

### Row Counts After Data Load

| Table | Rows |
|-------|------|
| platform | 2 |
| channel | 4 |
| twitter_user | 1 |
| post | 29,607 |
| engagement | 29,607 |
| sentiment | 29,607 |
| named_entity | 36 |
| post_entity | 44,128 |
| hashtag | 0 |
| post_hashtag | 0 |

> Note: `hashtag` and `post_hashtag` are empty because the Twitter API scrape did not return hashtag metadata for this collection. The schema and loader fully support hashtag population when data is available.

### Data Loading

Data was loaded from CSV files using the Python script `scripts/load_data.py`, which:
1. Reads each CSV with `csv.DictReader`
2. Inserts channels / users with `INSERT OR IGNORE` to deduplicate
3. Parses comma-separated `mentioned_leaders` and `mentioned_hotspots` into individual `named_entity` rows
4. Creates `post_entity` links for every entity-post pair
5. Inserts engagement and sentiment records linked by `post_id`

---

## Step 5 — Querying the Database

All queries were executed against `capstone2/data/politrace.db`. Results are shown below each query.

---

### Easy Query 1 — Posts per platform with sentiment distribution

**What it does:** Counts total posts per platform, computes average sentiment score, and breaks down posts by sentiment label. Uses 2 joined tables (post + platform + sentiment), GROUP BY, COUNT, AVG, and conditional SUM.

```sql
SELECT
    p.name                          AS platform,
    COUNT(po.post_id)               AS total_posts,
    ROUND(AVG(s.score), 4)          AS avg_sentiment_score,
    SUM(CASE WHEN s.label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
    SUM(CASE WHEN s.label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
    SUM(CASE WHEN s.label = 'neutral'  THEN 1 ELSE 0 END) AS neutral_count
FROM post po
JOIN platform p  ON po.platform_id = p.platform_id
JOIN sentiment s ON s.post_id = po.post_id
GROUP BY p.name
ORDER BY total_posts DESC;
```

**Result:**

| platform | total_posts | avg_sentiment_score | positive_count | negative_count | neutral_count |
|----------|-------------|---------------------|----------------|----------------|---------------|
| telegram | 15,000 | −0.1876 | 4,526 | 7,703 | 2,771 |
| twitter | 14,607 | −0.1956 | 3,421 | 7,244 | 3,942 |

**Insight:** Both platforms show overall negative sentiment (avg ~−0.19), reflecting the geopolitical crisis nature of the dataset. Twitter is marginally more negative. Negative posts outnumber positive by ~1.7× on Telegram and ~2.1× on Twitter.

---

### Easy Query 2 — Top Telegram channels by post count

**What it does:** Ranks all Telegram channels by number of posts collected, showing average and max view counts alongside subscriber numbers. Uses 2 tables (post + channel), GROUP BY, COUNT, AVG, MAX, ORDER BY.

```sql
SELECT
    c.channel_name,
    COUNT(po.post_id)        AS total_posts,
    ROUND(AVG(po.views), 0)  AS avg_views,
    MAX(po.views)            AS max_views,
    c.channel_subscribers
FROM post po
JOIN channel c ON po.channel_id = c.channel_id
GROUP BY c.channel_id
ORDER BY total_posts DESC
LIMIT 10;
```

**Result:**

| channel_name | total_posts | avg_views | max_views | channel_subscribers |
|---|---|---|---|---|
| Reuters: World | 5,928 | 3,286 | 76,144 | 48,863 |
| BBC News (World) | 5,928 | 1,657 | 49,639 | 24,775 |
| The New York Times | 2,804 | 29,147 | 735,675 | 176,492 |
| Disclose.tv | 340 | 70,801 | 1,747,198 | 339,630 |

**Insight:** Reuters and BBC produced equal post volumes. NYT has ~9× higher average views despite fewer posts, indicating more viral content. Disclose.tv has the highest avg views (70,801) and max views (1.7M) despite fewest posts — its content provokes significantly higher engagement.

---

### Medium Query 1 — Most mentioned leaders with sentiment breakdown

**What it does:** Identifies the most discussed political leaders across both platforms, shows total mention count, average sentiment score, and breakdown by sentiment label. Joins 4 tables (named_entity + post_entity + sentiment + post), filters by entity_type, uses COUNT DISTINCT, AVG, conditional SUM, ORDER BY.

```sql
SELECT
    ne.name                     AS leader,
    COUNT(DISTINCT pe.post_id)  AS mentions,
    ROUND(AVG(s.score), 4)      AS avg_sentiment,
    SUM(CASE WHEN s.label = 'positive' THEN 1 ELSE 0 END) AS pos,
    SUM(CASE WHEN s.label = 'negative' THEN 1 ELSE 0 END) AS neg,
    SUM(CASE WHEN s.label = 'neutral'  THEN 1 ELSE 0 END) AS neu
FROM named_entity ne
JOIN post_entity pe  ON pe.entity_id = ne.entity_id
JOIN sentiment s     ON s.post_id = pe.post_id
JOIN post po         ON po.post_id = pe.post_id
WHERE ne.entity_type = 'leader'
GROUP BY ne.entity_id
ORDER BY mentions DESC
LIMIT 12;
```

**Result:**

| leader | mentions | avg_sentiment | pos | neg | neu |
|---|---|---|---|---|---|
| Trump | 3,291 | −0.2443 | 875 | 1,943 | 473 |
| Putin | 2,157 | −0.3419 | 494 | 1,410 | 253 |
| Netanyahu | 1,874 | −0.2711 | 374 | 1,039 | 461 |
| Biden | 1,018 | −0.2768 | 306 | 641 | 71 |
| Zelensky | 926 | −0.2767 | 247 | 539 | 140 |
| Macron | 188 | −0.2091 | 53 | 94 | 41 |
| Musk | 164 | −0.0989 | 62 | 89 | 13 |
| Xi Jinping | 155 | −0.0453 | 68 | 72 | 15 |
| Modi | 116 | −0.1522 | 37 | 67 | 12 |
| Erdogan | 115 | −0.2029 | 36 | 65 | 14 |
| Harris | 70 | −0.1362 | 23 | 38 | 9 |
| Lavrov | 54 | −0.4147 | 9 | 41 | 4 |

**Insight:** Trump (3,291) and Putin (2,157) dominate coverage. Putin carries the most negative sentiment (−0.3419), and Lavrov is the most negatively covered leader (−0.4147). Xi Jinping and Musk are covered most neutrally (near 0). The top 3 leaders alone account for 57% of all leader mentions.

---

### Medium Query 2 — Top geopolitical hotspots per platform with engagement

**What it does:** For each platform, ranks the most discussed geopolitical hotspots (conflict zones, keywords) by mention count. Computes average post views, average interaction count (likes+retweets+forwards+replies+reactions), and average sentiment. Joins 6 tables, uses HAVING to filter low-volume hotspots, ORDER BY multi-column.

```sql
SELECT
    pl.name                           AS platform,
    ne.name                           AS hotspot,
    COUNT(DISTINCT pe.post_id)        AS mentions,
    ROUND(AVG(po.views), 0)           AS avg_views,
    ROUND(AVG(e.likes + e.retweets + e.forwards
              + e.replies + e.reactions), 1) AS avg_interactions,
    ROUND(AVG(s.score), 4)            AS avg_sentiment
FROM named_entity ne
JOIN post_entity pe ON pe.entity_id = ne.entity_id
JOIN post po        ON po.post_id = pe.post_id
JOIN platform pl    ON pl.platform_id = po.platform_id
JOIN engagement e   ON e.post_id = po.post_id
JOIN sentiment s    ON s.post_id = po.post_id
WHERE ne.entity_type = 'hotspot'
GROUP BY pl.platform_id, ne.entity_id
HAVING mentions >= 10
ORDER BY platform, mentions DESC
LIMIT 16;
```

**Result:**

| platform | hotspot | mentions | avg_views | avg_interactions | avg_sentiment |
|---|---|---|---|---|---|
| telegram | Russia | 2,961 | 21,714 | 179.5 | −0.4614 |
| telegram | Ukraine | 2,557 | 22,904 | 189.6 | −0.4748 |
| telegram | Israel | 897 | 22,143 | 121.0 | −0.5641 |
| telegram | Gaza | 569 | 23,223 | 110.7 | −0.5603 |
| telegram | Iran | 449 | 24,860 | 314.1 | −0.5141 |
| telegram | nuclear | 342 | 17,014 | 140.8 | −0.4242 |
| telegram | NATO | 331 | 16,715 | 126.0 | −0.2858 |
| telegram | sanctions | 220 | 16,282 | 134.5 | −0.4019 |
| telegram | coup | 166 | 10,995 | 59.8 | −0.3145 |
| telegram | Taiwan | 160 | 10,378 | 48.1 | −0.1690 |
| twitter | Ukraine | 5,387 | 1,039 | 0.0 | −0.2862 |

**Insight:** On Telegram, Iran-related posts generate highest avg interactions (314.1) despite fewer mentions than Russia/Ukraine. Israel and Gaza have the most negative sentiment (−0.56). Twitter shows Ukraine as the dominant hotspot by far (5,387 mentions). The Twitter engagement being 0.0 reflects missing engagement metadata in this collection batch.

---

### Difficult Query — Hotspot peak activity analysis with source attribution

**What it does:** A multi-layer analysis using 2 CTEs and 2 window functions. For each platform, identifies the top 6 hotspots by total mention volume, finds the peak activity month for each, and identifies which channel or source drove the most coverage in that peak month. Uses 7 joined tables, `strftime()` date function, `LEFT JOIN`, `CASE` expression, `ROW_NUMBER()` and `DENSE_RANK()` window functions, and nested subquery via CTEs.

```sql
WITH hotspot_monthly AS (
    SELECT
        pl.name                          AS platform,
        ne.name                          AS hotspot,
        strftime('%Y-%m', po.date)       AS month,
        COUNT(DISTINCT pe.post_id)       AS mentions,
        ROUND(AVG(s.score), 4)           AS avg_sentiment,
        SUM(e.likes + e.retweets + e.forwards + e.replies + e.reactions)
                                         AS total_interactions,
        SUM(po.views)                    AS total_views,
        CASE WHEN po.channel_id IS NOT NULL THEN c.channel_name
             ELSE 'Twitter feed' END     AS primary_source
    FROM named_entity ne
    JOIN post_entity pe ON pe.entity_id = ne.entity_id
    JOIN post po        ON po.post_id = pe.post_id
    JOIN platform pl    ON pl.platform_id = po.platform_id
    JOIN sentiment s    ON s.post_id = po.post_id
    JOIN engagement e   ON e.post_id = po.post_id
    LEFT JOIN channel c ON c.channel_id = po.channel_id
    WHERE ne.entity_type = 'hotspot'
      AND po.date >= '2026-01-01'
      AND length(po.text) > 20
    GROUP BY pl.name, ne.entity_id, strftime('%Y-%m', po.date), primary_source
),
hotspot_totals AS (
    SELECT platform, hotspot, SUM(mentions) AS total_mentions
    FROM hotspot_monthly GROUP BY platform, hotspot
),
ranked AS (
    SELECT hm.*, ht.total_mentions,
           ROW_NUMBER() OVER (
               PARTITION BY hm.platform, hm.hotspot
               ORDER BY hm.mentions DESC
           ) AS peak_rn,
           DENSE_RANK() OVER (
               PARTITION BY hm.platform
               ORDER BY ht.total_mentions DESC
           ) AS platform_rank
    FROM hotspot_monthly hm
    JOIN hotspot_totals ht
      ON ht.platform = hm.platform AND ht.hotspot = hm.hotspot
)
SELECT platform, hotspot, total_mentions, month AS peak_month,
       mentions AS peak_month_count, avg_sentiment,
       total_interactions, total_views, primary_source
FROM ranked
WHERE peak_rn = 1 AND platform_rank <= 6
ORDER BY platform, platform_rank
LIMIT 14;
```

**Result:**

| platform | hotspot | total_mentions | peak_month | peak_count | avg_sentiment | total_interactions | total_views | primary_source |
|---|---|---|---|---|---|---|---|---|
| telegram | Iran | 85 | 2026-05 | 47 | −0.1442 | 78,784 | 3,003,847 | Disclose.tv |
| telegram | Israel | 26 | 2026-02 | 8 | −0.5117 | 1,923 | 274,621 | The New York Times |
| telegram | Russia | 25 | 2026-01 | 10 | −0.5988 | 2,845 | 325,297 | The New York Times |
| telegram | Ukraine | 17 | 2026-01 | 8 | −0.5701 | 2,363 | 259,951 | The New York Times |
| telegram | nuclear | 13 | 2026-05 | 5 | +0.2278 | 8,869 | 318,162 | Disclose.tv |
| telegram | Gaza | 8 | 2026-02 | 4 | −0.5352 | 942 | 127,808 | The New York Times |
| twitter | Ukraine | 5,337 | 2026-05 | 5,250 | −0.2965 | 0 | 5,584,193 | Twitter feed |
| twitter | Gaza | 4,390 | 2026-05 | 4,361 | −0.2605 | 0 | 4,199,299 | Twitter feed |
| twitter | Russia | 3,408 | 2026-05 | 3,380 | −0.2809 | 0 | 5,217,110 | Twitter feed |
| twitter | Israel | 2,577 | 2026-05 | 2,443 | −0.3549 | 0 | 2,996,110 | Twitter feed |
| twitter | Taiwan | 1,783 | 2026-05 | 1,783 | −0.0243 | 0 | 3,084,864 | Twitter feed |
| twitter | ceasefire | 1,633 | 2026-05 | 1,568 | −0.3939 | 0 | 2,835,338 | Twitter feed |

**Insight:** On Telegram, Iran dominates with 85 mentions — driven by Disclose.tv, which generated 3M total views and 78k interactions despite fewer overall posts (its provocative content generates outsized engagement). The Russia and Ukraine narratives peaked in January 2026, suggesting a conflict escalation at that time. Nuclear content shows rare positive sentiment (+0.23) on Telegram, possibly reflecting arms deal or ceasefire coverage. On Twitter, all top hotspots peak in May 2026 (the collection period), with Ukraine, Russia, and Taiwan generating 5M+ views.

---

## Summary

| Deliverable | Status |
|---|---|
| Step 1 — Dataset Summary | Done |
| Step 2 — Conceptual ERD (10 entities, relationships explained) | Done |
| Step 3 — Logical ERD (3NF normalized, normalization justified) | Done |
| Step 4 — Physical schema (SQL script + data load + row counts) | Done |
| Step 5 — 5 SQL queries with results (2 Easy, 2 Medium, 1 Difficult) | Done |

**Files:**
- `capstone2/schema/create_tables.sql` — DDL schema for all 10 tables
- `capstone2/scripts/load_data.py` — Python data loader from CP1 CSVs
- `capstone2/scripts/queries.sql` — All 5 SQL queries with embedded results
- `capstone2/data/politrace.db` — Populated SQLite database (29,607 posts)
