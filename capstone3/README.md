# Politrace — Capstone 3 Dashboards

Two interactive dashboards over the Capstone 2 SQLite database (~20,300 political posts from
Telegram & Twitter/X).

| Dashboard | Type | What it answers |
|-----------|------|-----------------|
| **Analytical** (`/analytical`) | Analytical | How negative is the conversation, and where does it come from? |
| **Strategic** (`/strategic`) | Strategic | Who/what dominates the agenda, and how is everything connected? (Obsidian-style co-mention graph) |

## Run

```bash
cd capstone3
pip install -r requirements.txt      # only Flask (DB access uses built-in sqlite3)
python app.py
```

Open **http://127.0.0.1:5000**. No internet needed — Chart.js and D3 are vendored in
`static/vendor/`.

## Project structure

```
capstone3/
├── app.py                  # Flask app: pages + JSON API
├── requirements.txt
├── backend/
│   ├── db.py               # sqlite3 connection layer
│   └── queries.py          # all optimized, parameterized SQL
├── sql/queries.sql         # the same queries, annotated, for submission
├── templates/              # index / analytical / strategic
├── static/
│   ├── css/style.css       # shared dark "Obsidian" theme
│   ├── js/                 # common.js, analytical.js, strategic.js
│   └── vendor/             # Chart.js + D3 (offline)
├── data/politrace.db       # SQLite DB (rebuilt from Capstone 1 CSVs)
├── docs/capstone3_report.md
└── screenshots/
```

## Rebuilding the database (if needed)

The DB is already populated. To rebuild from the cleaned Capstone 1 CSVs:

```bash
python ../capstone2/scripts/load_data.py   # writes capstone2/data/politrace.db
cp ../capstone2/data/politrace.db data/politrace.db
```

## Tech

Flask · SQLite (built-in sqlite3) · Chart.js · D3.js (force-directed graph) · vanilla JS.
