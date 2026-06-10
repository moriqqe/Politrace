# Capstone Project 3 — Dashboard Development

**Project:** Politrace — Political Discourse Intelligence
**Student:** Arsenii Linkin
**Data source:** Capstone 1 (collection & cleaning) → Capstone 2 (SQLite data model)
**Stack:** Python · Flask · SQLite (sqlite3) · Chart.js · D3.js · HTML/CSS/JS
**Deliverables:** 2 interactive dashboards, Flask back-end, optimized SQL, screenshots

---

## Step 1 — Dashboard Plan

### The story

The Politrace dataset holds **~20,300 political posts** from Telegram (4 international news
channels) and Twitter/X, collected over Jan–May 2026 and focused on geopolitics: the
Ukraine–Russia war, the Israel–Gaza conflict, sanctions, NATO and nuclear escalation.

Two questions drive the project:

1. **How negative is the global geopolitics conversation, and where does that negativity come
   from?** (sentiment, time, platform, channel)
2. **Who and what dominates the agenda, and how are the players connected?** (leaders and
   hotspots, and how often they are mentioned together)

Because these are two different jobs — one *analytical* (explain the past in detail) and one
*strategic* (see the whole board at a glance) — the project ships **two dashboards of
different types**, as the rubric requires.

### Dashboard 1 — Analytical

| | |
|---|---|
| **Type** | **Analytical** — supports exploration and root-cause analysis |
| **Target users** | Data analysts, journalists, researchers digging into *why* sentiment moves |
| **Story** | "The conversation is overwhelmingly negative (56%). Twitter is angrier than Telegram, negativity spikes around major events, and the loudest channels are the wire services." |
| **Key metrics** | Total posts, average VADER sentiment, negative share, average reach (views), average post length |
| **Visualizations** | (1) Volume + sentiment time series, (2) sentiment doughnut, (3) platform-comparison stacked bar, (4) top-channels bar, (5) word-count histogram, (6) reach-vs-engagement scatter, (7) most-viewed posts table |
| **Interactivity** | Platform / sentiment / date-range filters, full-text search, live-updating table |

### Dashboard 2 — Strategic

| | |
|---|---|
| **Type** | **Strategic** — high-level overview for fast situational awareness |
| **Target users** | Editors, decision-makers, OSINT leads who need the big picture in one screen |
| **Story** | "A handful of entities — Ukraine, Russia, Gaza, Israel, Trump — anchor the entire discourse, and they cluster into two tightly-linked theatres of conflict." |
| **Key metrics** | Posts in scope, leaders tracked, hotspots tracked, total entity mentions, overall tone |
| **Visualizations** | (1) **Obsidian-style co-mention network graph** (the centerpiece), (2) topic tag-cloud, (3) sentiment-by-entity diverging bars, (4) hotspot leaderboard table, (5) KPI summary |
| **Interactivity** | Same global filter bar + entity-type toggle (all / leaders / hotspots), link-strength slider, drag / zoom / hover-spotlight / click-to-pin on the graph |

### Why these chart choices

The data mixes **quantitative** fields (counts, views, sentiment scores, word counts) with
**qualitative / categorical** structure (platform, sentiment label, entity type, and the
many-to-many co-mention relationships). The chart set is chosen to cover both, and to satisfy
the rubric's "≥4 quantitative, ≥3 qualitative" rule (see Step 5).

---

## Step 2 — Database Integration

### Connection

The dashboards read directly from the **Capstone 2 SQLite database** (`data/politrace.db`).
The connection layer (`backend/db.py`) uses Python's built-in **`sqlite3`** module — a fresh,
short-lived connection per query, which is thread-safe under Flask's dev server and keeps the
project dependency-free (only Flask is required). `sqlite3` supports the same `:name` bound
parameters as SQLAlchemy, so every query stays parameterized:

```python
import sqlite3

def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row      # rows behave like dicts
    return conn

def fetch_all(sql, params=None):
    conn = _connect()
    try:
        cur = conn.execute(sql, params or {})   # :name params, no string-building
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
```

> **Note on rebuilding the DB.** The `politrace.db` shipped with Capstone 2 was empty (the file
> never persisted), so the database was rebuilt from the cleaned Capstone 1 CSVs using the
> existing `capstone2/scripts/load_data.py` loader. Final row counts: **20,329 posts**,
> 4 channels, 36 named entities (21 leaders + 15 hotspots) and **27,916 post↔entity links**.

### Optimized retrieval

* Every dashboard query joins on the **indexed** columns defined in the Capstone 2 schema:
  `post(platform_id, channel_id, date)`, `sentiment(post_id, label)`,
  `post_entity(entity_id)`, `engagement(post_id)`.
* All aggregation (`COUNT`, `AVG`, `SUM(CASE WHEN…)`, `GROUP BY`) happens **in SQL**, not in
  Python, so only small result sets cross the wire.
* The global filter bar is compiled into a **single reusable parameterized `WHERE` clause**
  (`backend/queries.py::_filters`) shared by every endpoint — values are always bound
  parameters (`:platform`, `:start`, `:end`, `:sentiment`, `:q`), which prevents SQL injection
  and lets SQLite reuse query plans.
* The co-mention network is computed with a **self-join on `post_entity`**
  (`pa.entity_id < pb.entity_id`) plus a `HAVING weight >= :min_weight` cut so the graph stays
  readable; the threshold is driven live from the UI slider.

The full annotated query set is in **`sql/queries.sql`**.

---

## Step 3 — Dashboard Design (Layout & UX)

* **Shared dark theme** (`static/css/style.css`) inspired by the Obsidian graph view — a single
  set of CSS variables drives both dashboards for visual consistency.
* **Logical placement:** a sticky top nav, then a global filter bar, then a KPI strip, then
  charts arranged most-important-first in a responsive CSS grid (collapses to one column on
  narrow screens).
* **Interactive elements:** dropdowns (platform, sentiment), date pickers, a debounced search
  box, an entity-type segmented control, and a link-strength range slider. The network graph
  adds drag, scroll-zoom, hover-spotlight and click-to-pin.
* **Widgets:** KPI cards, line/bar/doughnut/scatter/stacked charts, a force-directed graph, a
  tag cloud and live data tables.

---

## Step 4 — Develop the Dashboard

**Front-end:** HTML + CSS + vanilla JS. Chart.js renders the quantitative charts; D3.js (v7
force simulation) renders the network. Charts and the graph re-fetch and redraw whenever a
filter changes, so the two dashboards are fully dynamic. Chart.js and D3 are **vendored
locally** (`static/vendor/`) so the app runs with no internet connection.

**Back-end:** Flask (`app.py`) exposes the pages and a small JSON API. Each endpoint reads the
filter bar from the query string, runs the matching optimized SQL via sqlite3, and returns
JSON the front-end turns into a chart.

```
GET /                              landing page
GET /analytical                    Dashboard 1
GET /strategic                     Dashboard 2
GET /api/filters                   dropdown options + date bounds
GET /api/analytical/kpis|timeseries|sentiment|platform|channels|
        engagement|wordcount|posts
GET /api/strategic/kpis|network|entities|entity_sentiment|hotspots
```

All 17 routes were verified to return HTTP 200 with valid payloads, and filter combinations
(platform + sentiment + search + date) were confirmed to propagate to every chart and to the
network graph. Screenshots of the working dashboards are in **`screenshots/`**.

---

## Step 5 — Data Visualization

**Quantitative techniques (6 — requirement ≥4):**

1. **Time series** — daily post volume (bars) + mean sentiment (line), dual-axis.
2. **Histogram** — distribution of post word counts (binned).
3. **Ranked bar chart** — top channels by volume.
4. **Stacked bar chart** — sentiment composition per platform.
5. **Scatter plot** — reach (views) vs engagement, log–log.
6. **Diverging bar chart** — average sentiment per top entity.

**Qualitative techniques (4 — requirement ≥3):**

1. **Node-link network diagram** — entity co-mention graph (the Obsidian-style centerpiece);
   encodes categorical type (color), magnitude (node size), tone (ring color) and relationship
   strength (edge width).
2. **Categorical part-to-whole** — sentiment doughnut.
3. **Tag / word cloud** — entities sized by share of mentions.
4. **Detail tables** — most-viewed posts and hotspot leaderboard with categorical badges.

Performance: aggregation is pushed to SQLite, result sets are capped (e.g. scatter sampled to
600 points, network thresholded), and the libraries are local — so each view renders in well
under a second.

---

## Step 6 — UX & Testing

UX considerations integrated into the build:

* **Intuitive** — one consistent filter bar controls both dashboards; the same colors always
  mean the same thing (purple = leader, cyan = hotspot, green/amber/red = positive/neutral/
  negative).
* **Readable charts** — every panel has a one-line "what am I looking at" hint; tooltips give
  exact numbers on hover; the network labels only the biggest nodes by default and reveals the
  rest on hover so the canvas never gets noisy.
* **Discoverability** — the graph panel spells out its gestures ("drag · scroll to zoom · hover
  to spotlight · click to pin").
* **Responsiveness** — the grid reflows to a single column under 1000 px; the graph re-centers
  on window resize.
* **Efficiency** — local vendored libraries + SQL-side aggregation keep load times low; the
  slider and search box are debounced to avoid redundant queries.
* **Robustness** — empty filter results show a friendly "no posts match" message instead of a
  broken chart.

Testing performed: all 17 endpoints checked for 200 + valid JSON; filter-combination smoke
tests (platform/sentiment/search/date) confirmed correct propagation; both dashboards
rendered headlessly and captured as the screenshots in `screenshots/`.

---

## How to run

```bash
cd capstone3
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

No internet required — Chart.js and D3 are bundled in `static/vendor/`.
