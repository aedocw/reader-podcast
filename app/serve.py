"""Bottle web routes for Reader Podcast."""

import asyncio
import json
import logging
import os

import bottle
from bottle import Bottle, request, response, abort, static_file, template, redirect

from app.config import PORT, MP3_DIR, DEFAULT_VOICE
from app.db import (
    init_db,
    create_user,
    get_user_by_api_key,
    get_user_by_feed_token,
    create_episode,
    get_episodes_for_user,
    get_db,
)
from app.auth import require_user, require_admin
from app.feed_gen import generate_feed
from app.rss_monitor import mark_existing_as_seen
from app.scraper import scrape
from app.worker import start_workers

log = logging.getLogger(__name__)

app = Bottle()

# Tell Bottle where to find templates
bottle.TEMPLATE_PATH = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
]


# ── Public routes ──────────────────────────────────────────

@app.route("/")
def home():
    return "Reader Podcast is running. Use /add?key=YOUR_KEY to add articles."


@app.route("/feed/<token>")
def feed(token):
    """Per-user RSS feed, authenticated by feed token in URL."""
    user = get_user_by_feed_token(token)
    if not user:
        abort(404, "Feed not found")
    response.content_type = "application/rss+xml; charset=utf-8"
    return generate_feed(user)


@app.route("/mp3/<filename:path>")
def serve_mp3(filename):
    """Serve MP3 files from the data/mp3 directory."""
    file_path = os.path.join(MP3_DIR, filename)
    if os.path.exists(file_path):
        return static_file(filename, root=MP3_DIR, mimetype="audio/mpeg")
    abort(404, "File not found")


@app.route("/logo.jpg")
def logo():
    return static_file("logo.jpg", root=".", mimetype="image/jpeg")


# ── User-authenticated routes ─────────────────────────────

@app.route("/add", method=["GET", "POST"])
@require_user
def add_url(user):
    """Add article form. POST scrapes title and creates a pending episode for the worker."""
    message = ""
    error = False
    if request.method == "POST":
        url = request.forms.get("url")
        voice = request.forms.get("voice") or user["default_voice"]
        if not url:
            message = "URL is required"
            error = True
        else:
            try:
                article = scrape(url)
                create_episode(user["id"], article.title, url, voice)
                message = f"Queued '{article.title}' for processing."
            except Exception as e:
                log.exception("Failed to scrape article: %s", url)
                message = f"Error: {e}"
                error = True

    episodes = get_episodes_for_user(user["id"])
    has_active = any(ep["status"] in ("pending", "processing") for ep in episodes)
    voices = _get_english_voices()
    return template(
        "add",
        message=message,
        error=error,
        episodes=episodes,
        has_active=has_active,
        voices=voices,
        default_voice=user["default_voice"],
        feed_token=user["feed_token"],
    )


@app.route("/episodes")
@require_user
def episodes(user):
    """JSON list of episodes for the authenticated user."""
    status = request.query.get("status")
    eps = get_episodes_for_user(user["id"], status=status or None)
    response.content_type = "application/json"
    return json.dumps([dict(ep) for ep in eps])


@app.route("/voices")
def voices():
    """List available Edge TTS English voices."""
    response.content_type = "application/json"
    return json.dumps(_get_english_voices())


@app.route("/subscriptions", method=["GET", "POST"])
@require_user
def subscriptions(user):
    """Manage RSS subscriptions."""
    message = ""
    error = False
    conn = get_db()
    try:
        if request.method == "POST":
            feed_url = request.forms.get("feed_url")
            if feed_url:
                import feedparser
                feed = feedparser.parse(feed_url)
                title = feed.feed.get("title", "") if feed.feed else ""
                cur = conn.execute(
                    "INSERT INTO subscriptions (user_id, feed_url, title) VALUES (?, ?, ?)",
                    (user["id"], feed_url, title or None),
                )
                conn.commit()
                sub_id = cur.lastrowid
                # Mark all existing feed items as seen
                count = mark_existing_as_seen(sub_id, feed_url)
                display = title or feed_url
                message = f"Subscribed to {display} ({count} existing articles marked as seen)"
        subs = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return template(
        "subscriptions",
        message=message,
        error=error,
        subscriptions=subs,
        key=request.query.get("key"),
    )


@app.route("/subscriptions/<sub_id:int>/toggle", method=["POST"])
@require_user
def toggle_subscription(sub_id, user):
    """Toggle a subscription active/inactive."""
    conn = get_db()
    try:
        sub = conn.execute(
            "SELECT * FROM subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, user["id"]),
        ).fetchone()
        if not sub:
            abort(404, "Subscription not found")
        new_active = 0 if sub["active"] else 1
        conn.execute("UPDATE subscriptions SET active = ? WHERE id = ?", (new_active, sub_id))
        conn.commit()
    finally:
        conn.close()
    redirect(f"/subscriptions?key={request.query.get('key', '')}")


@app.route("/subscriptions/<sub_id:int>/delete", method=["POST"])
@require_user
def delete_subscription(sub_id, user):
    """Delete a subscription and its seen_articles records."""
    conn = get_db()
    try:
        sub = conn.execute(
            "SELECT * FROM subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, user["id"]),
        ).fetchone()
        if not sub:
            abort(404, "Subscription not found")
        conn.execute("DELETE FROM seen_articles WHERE subscription_id = ?", (sub_id,))
        conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
        conn.commit()
    finally:
        conn.close()
    redirect(f"/subscriptions?key={request.query.get('key', '')}")


# ── Admin routes ───────────────────────────────────────────

@app.route("/admin/users", method=["GET", "POST"])
@require_admin
def admin_users():
    """Create and list users."""
    if request.method == "POST":
        username = request.forms.get("username")
        voice = request.forms.get("default_voice") or DEFAULT_VOICE
        if not username:
            abort(400, "username is required")
        user = create_user(username, voice)
        response.content_type = "application/json"
        return json.dumps(dict(user))

    conn = get_db()
    try:
        users = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    finally:
        conn.close()
    response.content_type = "application/json"
    return json.dumps([dict(u) for u in users])


@app.route("/admin/users/<user_id:int>", method=["DELETE"])
@require_admin
def admin_delete_user(user_id):
    """Delete a user and their episodes."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM episodes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    return json.dumps({"deleted": user_id})


# ── Voice helpers ──────────────────────────────────────────

_voice_cache = None


def _get_english_voices():
    """Return list of English Edge TTS voice short names, cached."""
    global _voice_cache
    if _voice_cache is not None:
        return _voice_cache
    try:
        import edge_tts
        all_voices = asyncio.run(edge_tts.list_voices())
        _voice_cache = sorted(
            v["ShortName"] for v in all_voices
            if v.get("Locale", "").startswith("en-")
        )
    except Exception:
        log.exception("Failed to fetch Edge TTS voices")
        _voice_cache = [DEFAULT_VOICE]
    return _voice_cache


# ── Entry point ────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    start_workers()
    log.info("Starting Reader Podcast on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT, debug=True, reloader=False)


if __name__ == "__main__":
    main()
