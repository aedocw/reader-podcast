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
```
