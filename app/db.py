import os
import sqlite3
import uuid
from datetime import datetime, timezone

from app.config import DATABASE_PATH, MP3_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    default_voice TEXT NOT NULL,
    feed_token TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    mp3_filename TEXT,
    file_size INTEGER,
    voice TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    feed_url TEXT NOT NULL,
    title TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    poll_interval_minutes INTEGER NOT NULL DEFAULT 60,
    last_polled_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS seen_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
    article_url TEXT NOT NULL,
    seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    episode_id INTEGER REFERENCES episodes(id)
);
"""


def get_db():
    """Get a SQLite connection with WAL mode and Row factory."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist. Also ensures data directories exist."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    os.makedirs(MP3_DIR, exist_ok=True)
    os.makedirs("data/tmp", exist_ok=True)
    conn = get_db()
    conn.executescript(_SCHEMA)
    conn.close()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── User CRUD ──────────────────────────────────────────────

def create_user(username, default_voice="en-US-AndrewNeural"):
    """Create a new user with generated api_key and feed_token. Returns the user Row."""
    api_key = str(uuid.uuid4())
    feed_token = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, api_key, default_voice, feed_token) VALUES (?, ?, ?, ?)",
            (username, api_key, default_voice, feed_token),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
        return user
    finally:
        conn.close()


def get_user_by_api_key(api_key):
    """Look up a user by API key. Returns Row or None."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    finally:
        conn.close()


def get_user_by_feed_token(feed_token):
    """Look up a user by feed token. Returns Row or None."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE feed_token = ?", (feed_token,)).fetchone()
    finally:
        conn.close()


# ── Episode CRUD ───────────────────────────────────────────

def create_episode(user_id, title, source_url, voice):
    """Create a new pending episode. Returns the episode Row."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO episodes (user_id, title, source_url, voice) VALUES (?, ?, ?, ?)",
            (user_id, title, source_url, voice),
        )
        conn.commit()
        return conn.execute("SELECT * FROM episodes WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_episodes_for_user(user_id, status=None):
    """Get episodes for a user, optionally filtered by status. Returns list of Rows."""
    conn = get_db()
    try:
        if status:
            return conn.execute(
                "SELECT * FROM episodes WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (user_id, status),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM episodes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


def update_episode_status(episode_id, status, error_message=None, mp3_filename=None, file_size=None):
    """Update episode status and optional fields."""
    conn = get_db()
    try:
        fields = ["status = ?"]
        values = [status]
        if error_message is not None:
            fields.append("error_message = ?")
            values.append(error_message)
        if mp3_filename is not None:
            fields.append("mp3_filename = ?")
            values.append(mp3_filename)
        if file_size is not None:
            fields.append("file_size = ?")
            values.append(file_size)
        if status == "done":
            fields.append("published_at = ?")
            values.append(_now())
        values.append(episode_id)
        conn.execute(f"UPDATE episodes SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()
