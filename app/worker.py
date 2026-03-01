"""Background worker threads for TTS processing."""

import logging
import os
import threading
import time

from app.config import MP3_DIR, RSS_POLL_INTERVAL_SECONDS
from app.db import get_db, update_episode_status
from app.rss_monitor import poll_all_due
from app.scraper import scrape
from app.tts import synthesize

log = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds between checking for pending episodes


def _cleanup_interrupted():
    """Reset any 'processing' episodes back to 'pending' on startup.

    These were interrupted by a previous crash/restart.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE episodes SET status = 'pending' WHERE status = 'processing'"
        )
        conn.commit()
        if cur.rowcount:
            log.info("Reset %d interrupted episodes back to pending", cur.rowcount)
    finally:
        conn.close()


def _get_next_pending():
    """Get the oldest pending episode, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM episodes WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()


def _process_episode(episode):
    """Process a single episode: scrape, synthesize, update status."""
    episode_id = episode["id"]
    log.info("Processing episode %d: %s", episode_id, episode["title"])
    update_episode_status(episode_id, "processing")

    try:
        if episode["body_text"]:
            paragraphs = [p for p in episode["body_text"].split("\n\n") if p.strip()]
        else:
            article = scrape(episode["source_url"])
            paragraphs = article.paragraphs
        mp3_filename = f"episode_{episode_id}.mp3"
        output_path = os.path.join(MP3_DIR, mp3_filename)

        file_size = synthesize(paragraphs, episode["voice"], output_path)
        update_episode_status(
            episode_id, "done",
            mp3_filename=mp3_filename, file_size=file_size,
        )
        log.info("Episode %d done: %s (%d bytes)", episode_id, mp3_filename, file_size)
    except Exception as e:
        log.exception("Episode %d failed: %s", episode_id, e)
        update_episode_status(episode_id, "error", error_message=str(e))


def _tts_worker_loop():
    """Main loop for the TTS worker thread. Polls for pending episodes."""
    log.info("TTS worker thread started")
    while True:
        try:
            episode = _get_next_pending()
            if episode:
                _process_episode(episode)
            else:
                time.sleep(POLL_INTERVAL)
        except Exception:
            log.exception("Unexpected error in TTS worker loop")
            time.sleep(POLL_INTERVAL)


def _rss_worker_loop():
    """Main loop for the RSS poller thread."""
    log.info("RSS poller thread started (interval: %ds)", RSS_POLL_INTERVAL_SECONDS)
    while True:
        try:
            new = poll_all_due()
            if new:
                log.info("RSS poller created %d new episodes", new)
        except Exception:
            log.exception("Unexpected error in RSS poller loop")
        time.sleep(RSS_POLL_INTERVAL_SECONDS)


def start_workers():
    """Start background worker threads. Call once at app startup."""
    _cleanup_interrupted()

    tts_thread = threading.Thread(target=_tts_worker_loop, daemon=True, name="tts-worker")
    tts_thread.start()

    rss_thread = threading.Thread(target=_rss_worker_loop, daemon=True, name="rss-poller")
    rss_thread.start()

    log.info("Background workers started")
