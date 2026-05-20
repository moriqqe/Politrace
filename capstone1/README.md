# Capstone 1

Capstone 1 — Political Discourse Data Collector. CLI tool for scraping Twitter/X, Instagram, and Telegram data on geopolitical topics.

## Setup

```bash
cd capstone1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env
```

Edit `.env` with your API keys before running scrapers.

## Run

```bash
python main.py --help
python main.py scrape twitter --defaults          # 1,500 tweets (default)
python main.py scrape instagram --defaults        # 1,500 posts (default)
python main.py scrape telegram --category western # 10,000 messages (default)
python main.py clean all
```

Limits are set in `.env` (`MAX_RECORDS_TWITTER`, `MAX_RECORDS_INSTAGRAM`, `MAX_RECORDS_TELEGRAM`) or via `--max`.
