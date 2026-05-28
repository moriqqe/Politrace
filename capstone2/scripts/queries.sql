-- =============================================================
-- Capstone Project 2 — SQL Queries (Step 5)
-- Database: SQLite  |  File: politrace.db
-- Dataset: Political Discourse — Telegram + Twitter
-- =============================================================


-- ─────────────────────────────────────────────────────────────
-- EASY QUERY 1
-- Total posts per platform with average sentiment score and
-- breakdown by sentiment label (positive / negative / neutral).
-- Tables used: post (2) + platform + sentiment
-- Aggregation: COUNT, AVG, conditional SUM
-- ─────────────────────────────────────────────────────────────
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

/*
RESULT:
  platform | total_posts | avg_sentiment_score | positive_count | negative_count | neutral_count
  telegram |       15000 |             -0.1876 |           4526 |           7703 |          2771
   twitter |       14607 |             -0.1956 |           3421 |           7244 |          3942
*/


-- ─────────────────────────────────────────────────────────────
-- EASY QUERY 2
-- Top Telegram channels ranked by post count, with avg views,
-- max views, and subscriber count.
-- Tables used: post + channel
-- Aggregation: COUNT, AVG, MAX  |  Sorting + LIMIT
-- ─────────────────────────────────────────────────────────────
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

/*
RESULT:
      channel_name | total_posts | avg_views | max_views | channel_subscribers
    Reuters: World |        5928 |    3286.0 |     76144 |               48863
  BBC News (World) |        5928 |    1657.0 |     49639 |               24775
  The New York Times|        2804 |   29147.0 |    735675 |              176492
       Disclose.tv |         340 |   70801.0 |   1747198 |              339630
*/


-- ─────────────────────────────────────────────────────────────
-- MEDIUM QUERY 1
-- Most mentioned political leaders across both platforms,
-- with average sentiment score and sentiment breakdown.
-- Tables used: named_entity + post_entity + sentiment + post (4)
-- Conditions: entity_type filter | Aggregation + ORDER BY
-- ─────────────────────────────────────────────────────────────
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

/*
RESULT:
    leader | mentions | avg_sentiment |  pos |  neg | neu
     Trump |     3291 |       -0.2443 |  875 | 1943 | 473
     Putin |     2157 |       -0.3419 |  494 | 1410 | 253
 Netanyahu |     1874 |       -0.2711 |  374 | 1039 | 461
     Biden |     1018 |       -0.2768 |  306 |  641 |  71
  Zelensky |      926 |       -0.2767 |  247 |  539 | 140
    Macron |      188 |       -0.2091 |   53 |   94 |  41
      Musk |      164 |       -0.0989 |   62 |   89 |  13
Xi Jinping |      155 |       -0.0453 |   68 |   72 |  15
      Modi |      116 |       -0.1522 |   37 |   67 |  12
   Erdogan |      115 |       -0.2029 |   36 |   65 |  14
    Harris |       70 |       -0.1362 |   23 |   38 |   9
    Lavrov |       54 |       -0.4147 |    9 |   41 |   4
*/


-- ─────────────────────────────────────────────────────────────
-- MEDIUM QUERY 2
-- Top geopolitical hotspots per platform: mention count,
-- average post views, average interaction count, avg sentiment.
-- Tables used: named_entity + post_entity + post + platform +
--              engagement + sentiment (6)
-- Conditions: entity_type filter, HAVING >= 10 mentions
-- Aggregation: COUNT, AVG | ORDER BY platform + mentions
-- ─────────────────────────────────────────────────────────────
SELECT
    pl.name                           AS platform,
    ne.name                           AS hotspot,
    COUNT(DISTINCT pe.post_id)        AS mentions,
    ROUND(AVG(po.views), 0)           AS avg_views,
    ROUND(AVG(e.likes + e.retweets + e.forwards + e.replies + e.reactions), 1)
                                      AS avg_interactions,
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

/*
RESULT:
  platform |    hotspot | mentions | avg_views | avg_interactions | avg_sentiment
  telegram |     Russia |     2961 |   21714.0 |            179.5 |       -0.4614
  telegram |    Ukraine |     2557 |   22904.0 |            189.6 |       -0.4748
  telegram |     Israel |      897 |   22143.0 |            121.0 |       -0.5641
  telegram |       Gaza |      569 |   23223.0 |            110.7 |       -0.5603
  telegram |       Iran |      449 |   24860.0 |            314.1 |       -0.5141
  telegram |     nuclear|      342 |   17014.0 |            140.8 |       -0.4242
  telegram |       NATO |      331 |   16715.0 |            126.0 |       -0.2858
  telegram |  sanctions |      220 |   16282.0 |            134.5 |       -0.4019
  ...
   twitter |    Ukraine |     5387 |    1039.0 |              0.0 |       -0.2862
*/


-- ─────────────────────────────────────────────────────────────
-- DIFFICULT QUERY
-- Per-platform hotspot analysis combining:
--   - total mention count across all months (CTE 1)
--   - peak activity month + peak source identification (CTE 2)
--   - platform-level ranking by total mentions (window function)
--   - sentiment, engagement, and view aggregation
-- Tables used: named_entity + post_entity + post + platform +
--              sentiment + engagement + channel (7 tables)
-- Techniques: 2 CTEs, 2 window functions (ROW_NUMBER + DENSE_RANK),
--   date function strftime(), LEFT JOIN, CASE expression,
--   nested aggregation, HAVING, ORDER BY multi-column
-- ─────────────────────────────────────────────────────────────
WITH hotspot_monthly AS (
    SELECT
        pl.name                                               AS platform,
        ne.name                                               AS hotspot,
        strftime('%Y-%m', po.date)                            AS month,
        COUNT(DISTINCT pe.post_id)                            AS mentions,
        ROUND(AVG(s.score), 4)                                AS avg_sentiment,
        SUM(e.likes + e.retweets + e.forwards + e.replies + e.reactions)
                                                              AS total_interactions,
        SUM(po.views)                                         AS total_views,
        CASE WHEN po.channel_id IS NOT NULL THEN c.channel_name
             ELSE 'Twitter feed'
        END                                                   AS primary_source
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
    FROM hotspot_monthly
    GROUP BY platform, hotspot
),
ranked AS (
    SELECT
        hm.*,
        ht.total_mentions,
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
SELECT
    platform,
    hotspot,
    total_mentions,
    month             AS peak_month,
    mentions          AS peak_month_count,
    avg_sentiment,
    total_interactions,
    total_views,
    primary_source
FROM ranked
WHERE peak_rn = 1
  AND platform_rank <= 6
ORDER BY platform, platform_rank
LIMIT 14;

/*
RESULT:
  platform |   hotspot | total_mentions | peak_month | peak_count | avg_sentiment | total_interactions | total_views |    primary_source
  telegram |      Iran |             85 |    2026-05 |         47 |       -0.1442 |              78784 |     3003847 |       Disclose.tv
  telegram |    Israel |             26 |    2026-02 |          8 |       -0.5117 |               1923 |      274621 | The New York Times
  telegram |    Russia |             25 |    2026-01 |         10 |       -0.5988 |               2845 |      325297 | The New York Times
  telegram |   Ukraine |             17 |    2026-01 |          8 |       -0.5701 |               2363 |      259951 | The New York Times
  telegram |   nuclear |             13 |    2026-05 |          5 |        0.2278 |               8869 |      318162 |       Disclose.tv
  telegram |      Gaza |              8 |    2026-02 |          4 |       -0.5352 |                942 |      127808 | The New York Times
   twitter |   Ukraine |           5337 |    2026-05 |       5250 |       -0.2965 |                  0 |     5584193 |      Twitter feed
   twitter |      Gaza |           4390 |    2026-05 |       4361 |       -0.2605 |                  0 |     4199299 |      Twitter feed
   twitter |    Russia |           3408 |    2026-05 |       3380 |       -0.2809 |                  0 |     5217110 |      Twitter feed
   twitter |    Israel |           2577 |    2026-05 |       2443 |       -0.3549 |                  0 |     2996110 |      Twitter feed
   twitter |    Taiwan |           1783 |    2026-05 |       1783 |       -0.0243 |                  0 |     3084864 |      Twitter feed
   twitter |  ceasefire|           1633 |    2026-05 |       1568 |       -0.3939 |                  0 |     2835338 |      Twitter feed
*/
