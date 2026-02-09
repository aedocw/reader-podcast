# CLAUDE.md

## Instructions for AI Assistants

- Always read PLANNING.md at the start of every new conversation
- Check TASKS.md before starting your work
- Mark completed tasks immediately in TASKS.md
- Add any newly discovered tasks to the appropriate milestone in TASKS.md
- Use uv for all package management (never pip)
- Follow existing code patterns in the app/ directory
- Keep it simple - this is a small project for up to 5 users

## Project Overview

**Reader Podcast** is a self-hosted web application that converts web articles into podcast episodes. It is a lightweight alternative to ListenLater.net.

Users submit article URLs (or subscribe to RSS feeds) and the system:
1. Scrapes article text using newspaper3k
2. Converts text to speech using Microsoft Edge TTS (cloud-based, async)
3. Generates per-user RSS 2.0 podcast feeds
4. Serves MP3 files for consumption in any podcast app

## Technology Stack

- **Language**: Python 3.x
- **Web Framework**: Bottle
- **Package Management**: uv
- **Environment**: .venv
- **Database**: SQLite (WAL mode)
- **TTS**: Microsoft Edge TTS (edge-tts library)
- **Deployment**: Docker behind Caddy (SSL), or direct Python/venv

## Key Commands

```bash
# Setup
uv sync                              # Install dependencies
uv run python -m app.serve           # Run the server

# Docker
docker build -t reader-podcast .
docker run -p 8025:8025 reader-podcast
```

## Project Structure

See PLANNING.md for full architecture details.

```
app/serve.py       - Web routes (Bottle)
app/db.py          - SQLite database layer
app/tts.py         - Edge TTS synthesis
app/scraper.py     - Article extraction
app/feed_gen.py    - RSS feed generation
app/rss_monitor.py - RSS feed polling
app/worker.py      - Background processing
app/config.py      - Configuration
app/auth.py        - Authentication
app/text_clean.py  - Text normalization
templates/         - Bottle HTML templates (add.html, subscriptions.html)
```

## Progress Summary

Milestones 1-5 are complete. The app is fully functional:

- **Milestone 1**: uv project init, `app/` package with `config.py` and `db.py` (SQLite WAL, 4 tables), `data/` directory structure
- **Milestone 2**: `text_clean.py` (quote/dash/whitespace normalization), `tts.py` (Edge TTS async parallel sentence synthesis with retries, pydub concatenation), `scraper.py` (newspaper3k + ScrapedArticle dataclass)
- **Milestone 3**: `auth.py` (require_user/require_admin decorators), `feed_gen.py` (dynamic per-user RSS 2.0), `serve.py` (15 routes: add, episodes, feed, mp3, voices, subscriptions, admin), HTML templates
- **Milestone 4**: `worker.py` (TTS daemon thread polling for pending episodes, startup cleanup), async `/add` POST (creates pending row, worker processes), auto-refresh UI
- **Milestone 5**: `rss_monitor.py` (feedparser polling, seen_articles tracking, mark-all-seen on subscribe), RSS poller daemon thread, subscription toggle/delete routes

**Milestone 6** (remaining): Dockerfile update, migration script (old feed.xml → SQLite), README update. Old root-level files have already been removed.

The old `mp3/` directory with existing episodes and `feed.xml` is preserved for the migration script.
