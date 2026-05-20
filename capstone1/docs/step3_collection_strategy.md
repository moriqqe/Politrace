# Step 3: Data Collection Strategy

**Capstone 1 — Political Discourse Data Collector**  
*Geopolitical discourse across Twitter/X, Instagram, and Telegram*

---

## 1. Collection Methods

### Twitter/X

Twitter data is collected through **API-mediated web scraping** on the Apify platform. The `TwitterScraper` class invokes the Apify actor `danek/twitter-scraper-ppr` via the `apify-client` Python SDK. Search terms are supplied from `config/keywords.yaml` (or overridden at runtime through the CLI). Each run returns structured tweet metadata—text, engagement counts, author information, hashtags, and URLs—which is normalized into a flat schema and written to disk.

This approach was chosen because the official Twitter/X API imposes restrictive access tiers and rate limits that are poorly suited to large-scale historical collection for research. Apify provides maintained scrapers, handles proxy rotation and anti-bot measures, and returns results in a dataset that integrates cleanly with Python. The trade-off is platform dependence and per-run cost, which is acceptable for a bounded one-time batch study.

### Instagram

Instagram follows the same architectural pattern. The `InstagramScraper` uses Apify actor `apify/instagram-scraper`, supporting **hashtag** and **profile** modes. Hashtag queries align with public discourse around geopolitical hotspots (e.g., `ukraine`, `gaza`); profile mode allows targeted collection from public accounts when needed. Post captions, engagement metrics, media type, and owner metadata are normalized before persistence.

Instagram’s official API is oriented toward business accounts and does not support broad keyword search at scale. Apify’s scraper accesses **public posts only**, without Instagram login credentials in this project, which limits ethical exposure while still yielding sufficient volume for discourse analysis.

### Telegram

Telegram data is collected with **Telethon**, a Python implementation of the MTProto client protocol. The `TelegramScraper` authenticates once (API ID, API hash, and phone number from `.env`), maintains a local session file, and iterates messages from **public channels** listed in `keywords.yaml` (categorized as pro-Kremlin, Western, or neutral trackers). Channel subscriber counts are retrieved via `GetFullChannelRequest` for contextual weighting.

Telegram was chosen because much geopolitical commentary in Eastern European and Middle Eastern conflicts circulates in public channels rather than on Western-centric platforms. Unlike Twitter and Instagram, Telegram does not offer a practical third-party scraping marketplace for channel history; direct MTProto access is the standard research approach for public channel archives.

---

## 2. Data Collection Frequency

The project adopts a **one-time batch collection** strategy. All scrapers run on demand through the CLI (`python main.py scrape …`), aggregate results up to a configurable ceiling (`MAX_RECORDS`, default 10,000 per platform), and persist snapshots with a `collection_date` timestamp.

This design is deliberate. The capstone aims to analyze a **historical cross-section** of political discourse around defined leaders and hotspots—not to operate a live monitoring dashboard. Batch collection avoids recurring API costs, simplifies reproducibility (fixed inputs in `keywords.yaml`), and matches typical academic workflows where datasets are frozen before cleaning, enrichment, and statistical or NLP analysis. Re-running the pipeline later can produce an updated snapshot, but continuous polling is out of scope.

---

## 3. Tools Used

| Tool / Library | Role in pipeline |
|----------------|------------------|
| **Apify platform** | Hosted actors for Twitter/X and Instagram scraping |
| **apify-client** (Python SDK) | Start actor runs, poll completion, iterate datasets |
| **Telethon** | MTProto client for public Telegram channel messages |
| **Typer** | Command-line interface (`scrape`, `clean`, subcommands) |
| **Rich** | Terminal UI: banners, progress bars, summary tables |
| **pandas** | CSV read/write, cleaning transforms |
| **VADER** (`vaderSentiment`) | Lexicon-based sentiment scores on text/captions |
| **PyYAML** | Keyword, query, and channel configuration |
| **python-dotenv** | Secure loading of API tokens and Telegram credentials |
| **tqdm** | Per-query progress during multi-query scrapes |

Supporting modules include a shared `BaseScraper` (save, deduplication, timestamps), `enrichment.py` (sentiment, word count, leader/hotspot matching), and platform-specific cleaners in `src/cleaning/`.

---

## 4. Storage Format

**CSV** is the primary storage format for both raw and cleaned data.

CSV was selected because it is human-readable, version-control friendly (within size limits), and universally supported by **pandas**, **Excel**, **R**, and visualization tools such as **Tableau**. JSON is supported as an optional export in the base scraper, but CSV remains the default for interoperability with the cleaning pipeline and downstream coursework.

### Folder structure

```
capstone1/
├── config/keywords.yaml      # Leaders, hotspots, queries, Telegram channels
├── data/
│   ├── raw/                  # Uncleaned scraper output (+ enrichment fields)
│   └── clean/                # Deduplicated, typed, validated CSVs
└── src/                      # Scrapers, cleaners, enrichment, CLI
```

Raw files retain scrape-time fields and enrichment columns (`sentiment_score`, `mentioned_leaders`, etc.). Clean files apply schema-specific rules (drop empty text, deduplicate by `tweet_id` / `post_id` / `message_id`, normalize datetimes, fill numeric nulls) and add `source_type = api_scrape` for provenance.

---

## 5. Authentication & Ethics

- **Twitter/X and Instagram:** Collection uses Apify actors that scrape **publicly visible content only**. No platform login is performed in this project; private accounts, direct messages, and non-public posts are excluded by design.
- **Telegram:** Collection requires **authenticated API access** (user API credentials), but targets only **public channels** named in the configuration file. No private chats, groups requiring membership beyond standard channel access, or user-level PII beyond what is already published on those channels are intentionally harvested.
- **Credentials:** Tokens and phone numbers reside in `.env` (excluded from version control via `.gitignore`). The repository ships `.env.example` without secrets.
- **Use:** Data is intended for academic discourse analysis on geopolitical topics, not for profiling individuals or commercial surveillance.

Researchers should remain aware of platform Terms of Service, regional privacy regulations, and the evolving legal status of scraping; this project documents methods transparently for scholarly review.

---

## 6. Record Volume Target

| Platform | Target records | Mechanism |
|----------|----------------|-----------|
| Twitter/X | 10,000 | `max_records` / `--max` cap per scrape batch |
| Instagram | 10,000 | Same |
| Telegram | 10,000 | Per-channel limits aggregated in `scrape_channels` |
| **Total** | **30,000** | Exceeds course minimum of 10,000 |

The default `MAX_RECORDS=10000` in `.env` enforces the ceiling in scraper constructors. Queries and channels are defined in `keywords.yaml` to diversify topical coverage (Ukraine, Gaza, NATO, sanctions, etc.) while staying within API budget and runtime constraints.

---

## Data Flow (End-to-End)

```
┌─────────────────────┐
│ config/keywords.yaml│  leaders, hotspots, search_queries, telegram_channels
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     Apify actors          ┌──────────────────┐
│  CLI (Typer)        │ ────────────────────────► │ TwitterScraper   │──┐
│  scrape twitter     │                           │ InstagramScraper │  │
│  scrape instagram   │     Telethon MTProto      └──────────────────┘  │
│  scrape telegram    │ ────────────────────────► │ TelegramScraper  │──┤
└──────────┬──────────┘                           └──────────────────┘  │
           │                                                              │
           ▼                                                              ▼
┌─────────────────────┐                                    ┌─────────────────────────┐
│ enrich_all()        │ ◄── VADER, word_count, keywords    │  data/raw/*_raw.csv     │
│ (enrichment.py)     │                                    │  (uncleaned + enriched) │
└──────────┬──────────┘                                    └────────────┬────────────┘
           │                                                              │
           │                    ┌─────────────────────┐                   │
           └──────────────────► │ clean_{platform}()  │ ◄─────────────────┘
                                │ (cleaning/)         │
                                └──────────┬──────────┘
                                           ▼
                                ┌─────────────────────────┐
                                │  data/clean/*_clean.csv │
                                │  (analysis-ready)       │
                                └──────────┬──────────────┘
                                           ▼
                                ┌─────────────────────────┐
                                │  Further analysis       │
                                │  (sentiment, NLP, viz)  │
                                └─────────────────────────┘
```

**Typical commands**

```bash
python main.py scrape twitter --defaults --max 10000
python main.py scrape instagram --defaults --max 10000
python main.py scrape telegram --category all --max 10000
python main.py clean all
```

---

*Document version: Step 3 — Collection strategy aligned with Capstone 1 implementation (Prompts 0–9).*
