# Reader Podcast - Planning

## Vision

A lightweight, self-hosted alternative to ListenLater.net. Convert web articles into podcast episodes using Microsoft Edge TTS. Subscribe to RSS feeds to automatically generate audio versions of new articles. Designed for a small user base (up to 5 users) running behind a reverse proxy.

## Architecture

### System Overview

```
User → Caddy (SSL) → Bottle Web App (port 8025)
                          ├── /add (submit URLs)
                          ├── /feed/<token> (per-user RSS feed)
                          ├── /mp3/<file> (audio files)
                          ├── /subscriptions (manage RSS subs)
                          ├── /voices (list Edge TTS voices)
                          └── /admin/* (user management)
                       ↕
                    SQLite DB (WAL mode)
                       ↕
              Background Workers (daemon threads)
                  ├── TTS Processor (polls pending episodes)
                  └── RSS Poller (checks subscriptions)
                       ↕
                  Edge TTS API (cloud, no GPU)
```

### Module Structure

```
app/
  __init__.py       - Package init
  serve.py          - Bottle routes and web UI
  db.py             - SQLite connection, schema init, CRUD helpers
  scraper.py        - Article extraction via newspaper3k
  tts.py            - Edge TTS: async parallel synthesis, audio combining
  feed_gen.py       - Dynamic per-user RSS 2.0 feed generation from DB
  rss_monitor.py    - RSS feed polling, new article detection
  worker.py         - Background thread manager (TTS queue + RSS poller)
  config.py         - Environment variable loading and defaults
  auth.py           - API key validation decorator
  text_clean.py     - Text normalization for TTS input
```

### Database Schema (SQLite)

**users** - id, username, api_key (UUID4), default_voice, feed_token (UUID4), created_at
**episodes** - id, user_id, title, source_url, mp3_filename, file_size, voice, status (pending/processing/done/error), error_message, created_at, published_at
**subscriptions** - id, user_id, feed_url, title, active, poll_interval_minutes, last_polled_at, created_at
**seen_articles** - id, subscription_id, article_url, seen_at, episode_id

### Edge TTS Pipeline

1. Split paragraphs → sentences (nltk sent_tokenize)
2. Parallel sentence synthesis: asyncio.Semaphore(10) + ThreadPoolExecutor
3. Each sentence: edge_tts.Communicate(text, voice).save(file) → MP3
4. 3 retries with 3s backoff per sentence
5. pydub AudioSegment concatenation: sentences → paragraphs (+ 600ms silence) → final MP3

### Background Workers

Two daemon threads running in the Bottle process:
- **TTS thread**: Polls episodes table for status='pending', processes one at a time FIFO
- **RSS thread**: Polls subscriptions table for feeds due for checking, creates pending episodes for new articles

### Authentication

- **User API key**: UUID4 per user, passed as ?key= or X-API-Key header
- **Feed token**: Separate UUID4 per user, embedded in feed URL for podcast apps (no auth needed)
- **Admin key**: Single env var for user management endpoints

## Technology Stack

- **Language**: Python 3.x
- **Web Framework**: Bottle
- **Package Management**: uv (always use for dependency management)
- **Environment**: Virtual environment (.venv)
- **Database**: SQLite (WAL mode)
- **TTS Engine**: Microsoft Edge TTS (edge-tts library)
- **Article Scraping**: newspaper3k
- **RSS Parsing**: feedparser
- **Audio Processing**: pydub + ffmpeg
- **Sentence Tokenization**: nltk (punkt tokenizer)
- **Deployment**: Docker container behind Caddy, or direct Python/venv

## Required Tools

- **Python 3.11+**
- **uv** - Python package manager
- **ffmpeg** - Audio encoding (required by pydub)
- **Docker** (optional) - Container deployment
- **Caddy** (production) - Reverse proxy with automatic SSL

## Environment Variables

```
SITE_URL=https://pod.example.com   # Required - base URL for feed/mp3 links
ADMIN_KEY=<secret>                  # Required - for /admin endpoints
PORT=8025                           # Optional (default: 8025)
DATABASE_PATH=data/reader.db       # Optional (default: data/reader.db)
MP3_DIR=data/mp3                   # Optional (default: data/mp3)
DEFAULT_VOICE=en-US-AndrewNeural   # Optional (default: en-US-AndrewNeural)
RSS_POLL_INTERVAL_SECONDS=3600     # Optional (default: 3600)
```

## Key Design Decisions

1. **Edge TTS over Kokoro**: Cloud-based, no GPU needed, async parallel processing, dramatically lighter Docker image (no torch)
2. **SQLite over Postgres**: No separate server, WAL mode handles concurrent access fine at 5 users, single-file backup
3. **In-process workers over Celery/Redis**: Simplicity wins at this scale; daemon threads die with the process
4. **Dynamic feed generation over static XML**: Database is source of truth; feed is a view, never stale
5. **Key-in-URL auth**: Simple, adequate for private instance behind SSL; separate feed tokens for podcast apps
6. **Sequential episode processing**: One TTS job at a time avoids Edge TTS rate limits; worst-case queue delay is minutes
