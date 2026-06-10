-- ============================================================================
-- Politrace — Capstone 3
-- SQL used for data retrieval & transformation behind the two dashboards.
-- DBMS: SQLite 3 (database built in Capstone 2: data/politrace.db)
--
-- All queries run against indexed columns:
--   post(platform_id, channel_id, date), sentiment(post_id, label),
--   post_entity(entity_id), engagement(post_id).
-- In the Flask app these appear with bound parameters (:platform, :start,
-- :end, :sentiment, :q) injected by backend/queries.py::_filters().
-- Below they are shown fully expanded for readability.
-- ============================================================================


-- ---------------------------------------------------------------------------
-- FILTER OPTIONS (populate dropdowns / date bounds)
-- ---------------------------------------------------------------------------
SELECT name FROM platform ORDER BY name;
SELECT channel_name FROM channel ORDER BY channel_name;
SELECT MIN(date) AS min_d, MAX(date) AS max_d FROM post;


-- ===========================================================================
--  DASHBOARD 1 — ANALYTICAL
-- ===========================================================================

-- KPI summary card row
SELECT
    COUNT(*)                                              AS total_posts,
    COUNT(DISTINCT po.channel_id)                         AS channels,
    ROUND(AVG(s.score), 4)                                AS avg_sentiment,
    ROUND(AVG(po.views))                                  AS avg_views,
    ROUND(AVG(po.word_count), 1)                          AS avg_words,
    SUM(CASE WHEN s.label = 'negative' THEN 1 ELSE 0 END) AS neg,
    SUM(CASE WHEN s.label = 'positive' THEN 1 ELSE 0 END) AS pos
FROM post po
JOIN platform  pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id  = po.post_id
LEFT JOIN channel   c ON c.channel_id = po.channel_id;

-- Time series: daily volume + mean sentiment (quantitative: line/bar combo)
SELECT substr(po.date, 1, 10)  AS day,
       COUNT(*)                AS posts,
       ROUND(AVG(s.score), 4)  AS avg_sentiment
FROM post po
JOIN platform pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
GROUP BY day
HAVING day >= '2025-01-01'
ORDER BY day;

-- Sentiment distribution (qualitative: categorical doughnut)
SELECT COALESCE(s.label, 'unknown') AS label, COUNT(*) AS n
FROM post po
LEFT JOIN sentiment s ON s.post_id = po.post_id
GROUP BY s.label
ORDER BY n DESC;

-- Platform comparison, stacked by sentiment (quantitative + qualitative)
SELECT pl.name                                            AS platform,
       COUNT(*)                                           AS posts,
       ROUND(AVG(s.score), 4)                             AS avg_sentiment,
       SUM(CASE WHEN s.label='negative' THEN 1 ELSE 0 END) AS negative,
       SUM(CASE WHEN s.label='neutral'  THEN 1 ELSE 0 END) AS neutral,
       SUM(CASE WHEN s.label='positive' THEN 1 ELSE 0 END) AS positive
FROM post po
JOIN platform pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
GROUP BY pl.name
ORDER BY posts DESC;

-- Top channels by volume (quantitative: ranked horizontal bar)
SELECT c.channel_name          AS channel,
       COUNT(*)                AS posts,
       ROUND(AVG(po.views))    AS avg_views,
       ROUND(AVG(s.score), 4)  AS avg_sentiment
FROM post po
JOIN platform pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
JOIN channel c ON c.channel_id = po.channel_id
WHERE po.channel_id IS NOT NULL
GROUP BY c.channel_id
ORDER BY posts DESC
LIMIT 8;

-- Word-count histogram (quantitative: distribution)
SELECT bucket, COUNT(*) AS n FROM (
    SELECT CASE
        WHEN word_count < 20  THEN '0-19'
        WHEN word_count < 40  THEN '20-39'
        WHEN word_count < 60  THEN '40-59'
        WHEN word_count < 80  THEN '60-79'
        WHEN word_count < 100 THEN '80-99'
        WHEN word_count < 150 THEN '100-149'
        ELSE '150+'
    END AS bucket
    FROM post
) GROUP BY bucket;

-- Reach vs engagement scatter (quantitative: scatter, log–log)
SELECT po.views                                          AS views,
       (e.reactions + e.forwards + e.likes + e.retweets) AS engagement,
       s.label                                           AS sentiment,
       po.word_count                                     AS words
FROM post po
JOIN engagement e ON e.post_id = po.post_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
WHERE po.views > 0
ORDER BY po.views DESC
LIMIT 600;

-- Most-viewed posts (qualitative: detail table)
SELECT substr(po.date,1,10)         AS date,
       pl.name                      AS platform,
       COALESCE(c.channel_name,'—') AS channel,
       s.label                      AS sentiment,
       po.views                     AS views,
       substr(po.text,1,160)        AS preview
FROM post po
JOIN platform pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
LEFT JOIN channel   c ON c.channel_id = po.channel_id
ORDER BY po.views DESC
LIMIT 40;


-- ===========================================================================
--  DASHBOARD 2 — STRATEGIC
-- ===========================================================================

-- KPI summary
SELECT COUNT(*) AS total_posts, ROUND(AVG(s.score),4) AS avg_sentiment
FROM post po LEFT JOIN sentiment s ON s.post_id = po.post_id;

SELECT SUM(entity_type='leader')  AS leaders,
       SUM(entity_type='hotspot') AS hotspots
FROM named_entity;

-- NETWORK NODES: each entity with mention count + average tone
SELECT n.entity_id            AS id,
       n.name                 AS name,
       n.entity_type          AS type,
       COUNT(*)               AS mentions,
       ROUND(AVG(s.score), 4) AS avg_sentiment
FROM post_entity pe
JOIN named_entity n ON n.entity_id = pe.entity_id
JOIN post po        ON po.post_id  = pe.post_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
GROUP BY n.entity_id;

-- NETWORK LINKS: co-mention weight between two entities in the same post
-- (qualitative: node-link / network diagram — the centerpiece visualization)
SELECT pa.entity_id AS source,
       pb.entity_id AS target,
       COUNT(*)     AS weight
FROM post_entity pa
JOIN post_entity pb
     ON pa.post_id = pb.post_id AND pa.entity_id < pb.entity_id
GROUP BY pa.entity_id, pb.entity_id
HAVING weight >= 40           -- adjustable from the UI slider
ORDER BY weight DESC;

-- Top entities (qualitative: tag/word cloud, sized by share)
SELECT n.name, n.entity_type AS type, COUNT(*) AS mentions,
       ROUND(AVG(s.score),4) AS avg_sentiment
FROM post_entity pe
JOIN named_entity n ON n.entity_id = pe.entity_id
JOIN post po        ON po.post_id  = pe.post_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
GROUP BY n.entity_id
ORDER BY mentions DESC
LIMIT 12;

-- Hotspot leaderboard
SELECT n.name, COUNT(*) AS mentions, ROUND(AVG(s.score),4) AS avg_sentiment
FROM post_entity pe
JOIN named_entity n ON n.entity_id = pe.entity_id
JOIN post po        ON po.post_id  = pe.post_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
WHERE n.entity_type = 'hotspot'
GROUP BY n.entity_id
ORDER BY mentions DESC
LIMIT 10;
