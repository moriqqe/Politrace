"""
Optimized SQL queries for the Politrace dashboards.

Every query joins onto the indexed columns (platform_id, channel_id, date,
sentiment.label, post_entity.entity_id) defined in the Capstone 2 schema, and
all user-controllable values are passed as bound parameters.

A single reusable WHERE-builder (`_filters`) keeps the global filter bar
(platform / date range / sentiment / free-text search) consistent across both
dashboards.
"""

from .db import fetch_all, fetch_one


# --------------------------------------------------------------------------- #
# Shared filter builder
# --------------------------------------------------------------------------- #
def _filters(args: dict) -> tuple[str, dict]:
    """Return ('AND ...', params) for the common filter bar.

    Expects keys: platform, start, end, sentiment, q  (all optional).
    Applies to a query where `post` is aliased as `po` and `sentiment` as `s`.
    """
    clauses = []
    params: dict = {}

    platform = args.get("platform")
    if platform and platform != "all":
        clauses.append("pl.name = :platform")
        params["platform"] = platform

    # Compare on the date-only portion so the bounds are inclusive of whole
    # calendar days. (post.date stores full timestamps like
    # "2026-05-27 22:12:57+00:00"; a plain string <= "2026-05-27" would wrongly
    # drop everything timestamped on the end day.)
    start = args.get("start")
    if start:
        clauses.append("substr(po.date,1,10) >= :start")
        params["start"] = start

    end = args.get("end")
    if end:
        clauses.append("substr(po.date,1,10) <= :end")
        params["end"] = end

    sentiment = args.get("sentiment")
    if sentiment and sentiment != "all":
        clauses.append("s.label = :sentiment")
        params["sentiment"] = sentiment

    q = args.get("q")
    if q:
        clauses.append("po.text LIKE :q")
        params["q"] = f"%{q}%"

    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where, params


# Base FROM used by most aggregate queries: post + platform + sentiment
_BASE = """
FROM post po
JOIN platform pl ON pl.platform_id = po.platform_id
LEFT JOIN sentiment s ON s.post_id = po.post_id
LEFT JOIN channel  c  ON c.channel_id = po.channel_id
WHERE 1 = 1
"""


# --------------------------------------------------------------------------- #
# Filter options (populate the dropdowns once)
# --------------------------------------------------------------------------- #
def filter_options() -> dict:
    platforms = fetch_all("SELECT name FROM platform ORDER BY name")
    channels = fetch_all(
        "SELECT channel_name FROM channel ORDER BY channel_name"
    )
    drange = fetch_one("SELECT MIN(date) AS min_d, MAX(date) AS max_d FROM post")
    return {
        "platforms": [p["name"] for p in platforms],
        "channels": [c["channel_name"] for c in channels],
        "sentiments": ["positive", "neutral", "negative"],
        "date_min": drange["min_d"],
        "date_max": drange["max_d"],
    }


# --------------------------------------------------------------------------- #
# DASHBOARD 1 — ANALYTICAL
# --------------------------------------------------------------------------- #
def kpis(args: dict) -> dict:
    where, p = _filters(args)
    sql = f"""
    SELECT
        COUNT(*)                                   AS total_posts,
        COUNT(DISTINCT po.channel_id)              AS channels,
        ROUND(AVG(s.score), 4)                     AS avg_sentiment,
        ROUND(AVG(po.views))                       AS avg_views,
        ROUND(AVG(po.word_count), 1)               AS avg_words,
        SUM(CASE WHEN s.label='negative' THEN 1 ELSE 0 END) AS neg,
        SUM(CASE WHEN s.label='positive' THEN 1 ELSE 0 END) AS pos
    {_BASE} {where}
    """
    row = fetch_one(sql, p) or {}
    total = row.get("total_posts") or 0
    neg = row.get("neg") or 0
    row["neg_pct"] = round(100 * neg / total, 1) if total else 0
    return row


def timeseries(args: dict) -> list[dict]:
    """Daily post volume + average sentiment."""
    where, p = _filters(args)
    sql = f"""
    SELECT substr(po.date, 1, 10)         AS day,
           COUNT(*)                       AS posts,
           ROUND(AVG(s.score), 4)         AS avg_sentiment
    {_BASE} {where}
    GROUP BY day
    HAVING day >= '2025-01-01'
    ORDER BY day
    """
    return fetch_all(sql, p)


def sentiment_distribution(args: dict) -> list[dict]:
    where, p = _filters(args)
    sql = f"""
    SELECT COALESCE(s.label,'unknown') AS label, COUNT(*) AS n
    {_BASE} {where}
    GROUP BY s.label
    ORDER BY n DESC
    """
    return fetch_all(sql, p)


def platform_compare(args: dict) -> list[dict]:
    where, p = _filters(args)
    sql = f"""
    SELECT pl.name                         AS platform,
           COUNT(*)                        AS posts,
           ROUND(AVG(s.score), 4)          AS avg_sentiment,
           SUM(CASE WHEN s.label='negative' THEN 1 ELSE 0 END) AS negative,
           SUM(CASE WHEN s.label='neutral'  THEN 1 ELSE 0 END) AS neutral,
           SUM(CASE WHEN s.label='positive' THEN 1 ELSE 0 END) AS positive
    {_BASE} {where}
    GROUP BY pl.name
    ORDER BY posts DESC
    """
    return fetch_all(sql, p)


def top_channels(args: dict, limit: int = 8) -> list[dict]:
    where, p = _filters(args)
    p["limit"] = limit
    sql = f"""
    SELECT c.channel_name                  AS channel,
           COUNT(*)                        AS posts,
           ROUND(AVG(po.views))            AS avg_views,
           ROUND(AVG(s.score), 4)          AS avg_sentiment
    {_BASE} {where}
      AND po.channel_id IS NOT NULL
    GROUP BY c.channel_id
    ORDER BY posts DESC
    LIMIT :limit
    """
    return fetch_all(sql, p)


def engagement_scatter(args: dict, limit: int = 600) -> list[dict]:
    """Sample of posts: views vs reactions+forwards, colored by sentiment."""
    where, p = _filters(args)
    p["limit"] = limit
    sql = f"""
    SELECT po.views                                   AS views,
           (e.reactions + e.forwards + e.likes + e.retweets) AS engagement,
           s.label                                    AS sentiment,
           po.word_count                              AS words
    FROM post po
    JOIN platform pl ON pl.platform_id = po.platform_id
    LEFT JOIN sentiment s ON s.post_id = po.post_id
    LEFT JOIN channel  c  ON c.channel_id = po.channel_id
    JOIN engagement e ON e.post_id = po.post_id
    WHERE po.views > 0 {where}
    ORDER BY po.views DESC
    LIMIT :limit
    """
    return fetch_all(sql, p)


def wordcount_histogram(args: dict) -> list[dict]:
    """Bucketed distribution of word counts."""
    where, p = _filters(args)
    sql = f"""
    SELECT bucket, COUNT(*) AS n FROM (
        SELECT CASE
            WHEN po.word_count < 20  THEN '0-19'
            WHEN po.word_count < 40  THEN '20-39'
            WHEN po.word_count < 60  THEN '40-59'
            WHEN po.word_count < 80  THEN '60-79'
            WHEN po.word_count < 100 THEN '80-99'
            WHEN po.word_count < 150 THEN '100-149'
            ELSE '150+'
        END AS bucket, po.word_count
        {_BASE} {where}
    )
    GROUP BY bucket
    """
    rows = {r["bucket"]: r["n"] for r in fetch_all(sql, p)}
    order = ['0-19', '20-39', '40-59', '60-79', '80-99', '100-149', '150+']
    return [{"bucket": b, "n": rows.get(b, 0)} for b in order]


def posts_table(args: dict, limit: int = 40) -> list[dict]:
    where, p = _filters(args)
    p["limit"] = limit
    sql = f"""
    SELECT substr(po.date,1,10)            AS date,
           pl.name                         AS platform,
           CASE WHEN pl.name = 'telegram' THEN c.channel_name
                ELSE COALESCE(NULLIF(u.user_name,'unknown'), 'Anonymous') END AS author,
           CASE WHEN pl.name = 'telegram' AND po.original_id <> ''
                THEN 'https://t.me/' || c.channel_username || '/' || po.original_id
                ELSE NULL END              AS url,
           s.label                         AS sentiment,
           po.views                        AS views,
           po.word_count                   AS words,
           substr(po.text,1,160)           AS preview
    FROM post po
    JOIN platform pl ON pl.platform_id = po.platform_id
    LEFT JOIN sentiment s ON s.post_id = po.post_id
    LEFT JOIN channel  c  ON c.channel_id = po.channel_id
    LEFT JOIN twitter_user u ON u.user_id = po.user_id
    WHERE 1 = 1 {where}
    ORDER BY po.views DESC
    LIMIT :limit
    """
    return fetch_all(sql, p)


# --------------------------------------------------------------------------- #
# DASHBOARD 2 — STRATEGIC
# --------------------------------------------------------------------------- #
def strategic_kpis(args: dict) -> dict:
    where, p = _filters(args)
    base = fetch_one(f"""
        SELECT COUNT(*) AS total_posts,
               ROUND(AVG(s.score),4) AS avg_sentiment
        {_BASE} {where}
    """, p) or {}
    ent = fetch_one("""
        SELECT
          SUM(CASE WHEN entity_type='leader'  THEN 1 ELSE 0 END) AS leaders,
          SUM(CASE WHEN entity_type='hotspot' THEN 1 ELSE 0 END) AS hotspots
        FROM named_entity
    """) or {}
    links = fetch_one("SELECT COUNT(*) AS mentions FROM post_entity") or {}
    base.update(ent)
    base["mentions"] = links.get("mentions", 0)
    return base


def network(args: dict, min_weight: int = 40, etype: str = "all") -> dict:
    """Entity co-mention network (Obsidian-style graph)."""
    where, p = _filters(args)
    p["minw"] = min_weight

    type_clause = ""
    if etype in ("leader", "hotspot"):
        type_clause = "AND n.entity_type = :etype"
        p["etype"] = etype

    node_sql = f"""
    SELECT n.entity_id                AS id,
           n.name                     AS name,
           n.entity_type              AS type,
           COUNT(*)                   AS mentions,
           ROUND(AVG(s.score), 4)     AS avg_sentiment
    FROM post_entity pe
    JOIN named_entity n ON n.entity_id = pe.entity_id
    JOIN post po        ON po.post_id  = pe.post_id
    JOIN platform pl    ON pl.platform_id = po.platform_id
    LEFT JOIN sentiment s ON s.post_id = po.post_id
    LEFT JOIN channel  c  ON c.channel_id = po.channel_id
    WHERE 1=1 {where} {type_clause}
    GROUP BY n.entity_id
    """
    nodes = fetch_all(node_sql, p)

    type_clause_b = type_clause.replace('n.entity_type', 'na.entity_type')
    extra_b = 'AND nb.entity_type = :etype' if etype in ('leader', 'hotspot') else ''
    link_sql = f"""
    SELECT pa.entity_id AS source, pb.entity_id AS target, COUNT(*) AS weight
    FROM post_entity pa
    JOIN post_entity pb
         ON pa.post_id = pb.post_id AND pa.entity_id < pb.entity_id
    JOIN post po     ON po.post_id = pa.post_id
    JOIN platform pl ON pl.platform_id = po.platform_id
    LEFT JOIN sentiment s ON s.post_id = po.post_id
    LEFT JOIN channel  c  ON c.channel_id = po.channel_id
    JOIN named_entity na ON na.entity_id = pa.entity_id
    JOIN named_entity nb ON nb.entity_id = pb.entity_id
    WHERE 1=1 {where} {type_clause_b} {extra_b}
    GROUP BY pa.entity_id, pb.entity_id
    HAVING weight >= :minw
    ORDER BY weight DESC
    """
    links = fetch_all(link_sql, p)

    linked_ids = {l["source"] for l in links} | {l["target"] for l in links}
    nodes = [n for n in nodes if n["id"] in linked_ids]
    return {"nodes": nodes, "links": links}


def top_entities(args: dict, etype: str = "all", limit: int = 12) -> list[dict]:
    where, p = _filters(args)
    p["limit"] = limit
    type_clause = ""
    if etype in ("leader", "hotspot"):
        type_clause = "AND n.entity_type = :etype"
        p["etype"] = etype
    sql = f"""
    SELECT n.name                 AS name,
           n.entity_type          AS type,
           COUNT(*)               AS mentions,
           ROUND(AVG(s.score),4)  AS avg_sentiment
    FROM post_entity pe
    JOIN named_entity n ON n.entity_id = pe.entity_id
    JOIN post po        ON po.post_id  = pe.post_id
    JOIN platform pl    ON pl.platform_id = po.platform_id
    LEFT JOIN sentiment s ON s.post_id = po.post_id
    LEFT JOIN channel  c  ON c.channel_id = po.channel_id
    WHERE 1=1 {where} {type_clause}
    GROUP BY n.entity_id
    ORDER BY mentions DESC
    LIMIT :limit
    """
    return fetch_all(sql, p)


def entity_sentiment(args: dict, limit: int = 10) -> list[dict]:
    """Avg sentiment for the most-mentioned entities (diverging bars)."""
    rows = top_entities(args, "all", limit)
    return sorted(rows, key=lambda r: (r["avg_sentiment"] or 0))


def hotspot_share(args: dict, limit: int = 10) -> list[dict]:
    """Share of discourse by hotspot (for treemap / tag cloud)."""
    return top_entities(args, "hotspot", limit)
