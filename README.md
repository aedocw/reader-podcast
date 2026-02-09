# Reader Podcast

A self-hosted web app that converts web articles into podcast episodes using Microsoft Edge TTS. Submit article URLs or subscribe to RSS feeds - the system scrapes the text, converts it to speech, and serves a per-user RSS podcast feed.

## Features

- Submit article URLs and get audio versions in your podcast app
- Subscribe to RSS feeds for automatic article-to-audio conversion
- Per-user podcast feeds with API key authentication
- 47 English voices via Microsoft Edge TTS (no GPU required)
- Background processing with status tracking
- Admin endpoints for user management

## Quick Start

### Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- ffmpeg (`brew install ffmpeg` or `apt install ffmpeg`)

### Setup

```bash
git clone https://github.com/aedocw/reader-podcast.git
cd reader-podcast
uv sync
```

### Configure

Create a `.env` file:

```
SITE_URL=https://pod.example.com   # Base URL for feed/mp3 links
ADMIN_KEY=your-secret-admin-key    # Required for /admin endpoints
PORT=8025                          # Optional (default: 8025)
DEFAULT_VOICE=en-US-AndrewNeural   # Optional (default: en-US-AndrewNeural)
```

### Create a User

```bash
# Start the server
uv run python -m app.serve

# In another terminal, create a user
curl -X POST "http://localhost:8025/admin/users?key=your-secret-admin-key" \
  -d "username=myname"
```

This returns the user's `api_key` and `feed_token`.

### Usage

- **Add articles**: Visit `http://localhost:8025/add?key=YOUR_API_KEY`
- **RSS feed**: Add `http://localhost:8025/feed/YOUR_FEED_TOKEN` to your podcast app
- **Manage subscriptions**: Visit `http://localhost:8025/subscriptions?key=YOUR_API_KEY`
- **List voices**: `GET http://localhost:8025/voices`

## Docker

```bash
docker build -t reader-podcast .
docker run -p 8025:8025 --env-file .env -v reader-podcast-data:/app/data reader-podcast
```

Example `docker-compose.yml`:

```yaml
services:
  reader-podcast:
    build: .
    container_name: reader-podcast
    env_file:
      - .env
    ports:
      - "8025:8025"
    volumes:
      - reader-podcast-data:/app/data
    restart: unless-stopped

volumes:
  reader-podcast-data:
```

## Migration from Old Version

If you have an existing `mp3/feed.xml` from the previous Kokoro TTS version:

```bash
uv run python migrate.py --username admin
```

This creates a user and imports all existing episodes into the new SQLite database.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SITE_URL` | `http://localhost:8025` | Base URL for feed/mp3 links |
| `ADMIN_KEY` | *(required)* | Secret key for admin endpoints |
| `PORT` | `8025` | Server port |
| `DATABASE_PATH` | `data/reader.db` | SQLite database path |
| `MP3_DIR` | `data/mp3` | MP3 file storage directory |
| `DEFAULT_VOICE` | `en-US-AndrewNeural` | Default Edge TTS voice |
| `RSS_POLL_INTERVAL_SECONDS` | `3600` | How often to check RSS subscriptions |

## Project Structure

```
app/
  serve.py        - Bottle web routes
  db.py           - SQLite database layer
  tts.py          - Edge TTS synthesis
  scraper.py      - Article extraction
  feed_gen.py     - RSS feed generation
  rss_monitor.py  - RSS feed polling
  worker.py       - Background processing
  config.py       - Configuration
  auth.py         - Authentication
  text_clean.py   - Text normalization
templates/        - HTML templates
```
