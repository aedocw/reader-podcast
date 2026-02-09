# Reader Podcast - Tasks

## Milestone 1: Project Infrastructure

- [ ] Initialize uv project with pyproject.toml (deps: bottle, python-dotenv, edge-tts, newspaper3k, pydub, nltk, feedparser, lxml)
- [ ] Create app/ package directory structure
- [ ] Implement app/config.py (env var loading with defaults)
- [ ] Implement app/db.py (SQLite connection helper, schema creation, CRUD functions)
- [ ] Create data/ directory structure (data/mp3/, data/tmp/) and update .gitignore

## Milestone 2: Core TTS Replacement

- [ ] Implement app/text_clean.py (whitespace normalization, quote straightening, punctuation collapsing)
- [ ] Implement app/tts.py (Edge TTS async parallel synthesis, pydub audio combining, retry logic)
- [ ] Implement app/scraper.py (refactor get_content.py with text cleaning, return dataclass)
- [ ] Test TTS pipeline end-to-end: URL → scrape → clean → synthesize → MP3

## Milestone 3: Web Application

- [ ] Implement app/auth.py (API key decorator, user resolution)
- [ ] Implement app/feed_gen.py (dynamic per-user RSS 2.0 generation from DB)
- [ ] Rewrite app/serve.py with all routes (add, episodes, feed, mp3, voices, settings, admin)
- [ ] Create templates/ (add.html with voice dropdown, subscriptions.html)
- [ ] Implement /voices endpoint (edge_tts.list_voices() filtered to English)
- [ ] Implement admin endpoints for user creation/management

## Milestone 4: Background Processing

- [ ] Implement app/worker.py (TTS processing thread + startup cleanup for interrupted jobs)
- [ ] Convert /add POST to async: create pending episode row, let worker process it
- [ ] Add episode status display in web UI (pending/processing/done/error)

## Milestone 5: RSS Feed Monitoring

- [ ] Implement app/rss_monitor.py (feedparser polling, new article detection, seen_articles tracking)
- [ ] Add RSS polling thread to worker.py
- [ ] Implement subscription management routes (add/remove/toggle)
- [ ] Create subscriptions.html template
- [ ] On new subscription: mark all existing feed items as seen (only process future articles)

## Milestone 6: Deployment & Migration

- [ ] Update Dockerfile (python:3.11-slim, uv, ffmpeg, no GPU)
- [ ] Write migration script: parse existing feed.xml → insert episodes into SQLite, create default user
- [ ] Update cli.py to use new modules
- [ ] Update README.md with new setup instructions
- [ ] Remove old files (read_content.py, get_content.py, write_feed.py, root serve.py, add_article_cli.py, requirements.txt, voices/)
