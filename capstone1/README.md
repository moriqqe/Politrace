# Capstone 1

Capstone 1 — Political Discourse Data Collector. CLI tool for scraping Twitter/X and Telegram data on geopolitical topics.

## Setup

```bash
cd capstone1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env
```

Edit `.env` with your API keys before running scrapers. Telegram phone must include country code (`+380...`).

## Run

```bash
python main.py --help
python main.py scrape twitter --defaults          # 15,000 tweets (default)
python main.py scrape telegram-login              # one-time Telegram auth
python main.py scrape telegram --category western # 15,000 messages (default)
python main.py clean all
```

Limits are set in `.env` (`MAX_RECORDS_TWITTER`, `MAX_RECORDS_TELEGRAM`) or via `--max`.

To continue after an interrupted scrape, use `--resume` (checkpoints in `data/raw/backups/`).

If the Telegram login code does not appear in the app, add `TELEGRAM_FORCE_SMS=1` to `.env` and run `telegram-login` again.
