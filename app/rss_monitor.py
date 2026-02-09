"""RSS feed polling: detect new articles and create pending episodes."""

import logging

import feedparser

from app.db import get_db, create_episode

log = logging.getLogger(__name__)


def get_due_subscriptions():
    """Get active subscriptions that are due for polling.

    A subscription is due if it has never been polled, or if
    (now - last_polled_at) >= poll_interval_minutes.
    """
    conn = get_db()
    try:
        return conn.execute("""
            SELECT s.*, u.default_voice, u.id as owner_id
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.active = 1
              AND (s.last_polled_at IS NULL
                   OR strftime('%s', 'now') - strftime('%s', s.last_polled_at)
                       >= s.poll_interval_minutes * 60)
        """).fetchall()
    finally:
        conn.close()


def mark_existing_as_seen(subscription_id, feed_url):
    """Mark all current entries in a feed as seen without creating episodes.

    Called when a new subscription is created so only future articles get processed.
    """
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return 0

    conn = get_db()
    try:
        count = 0
        for entry in feed.entries:
            link = entry.get("link", "")
            if not link:
                continue
            existing = conn.execute(
                "SELECT id FROM seen_articles WHERE subscription_id = ? AND article_url = ?",
                (subscription_id, link),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO seen_articles (subscription_id, article_url) VALUES (?, ?)",
                    (subscription_id, link),
                )
                count += 1
        conn.commit()
        log.info("Marked %d existing articles as seen for subscription %d", count, subscription_id)
        return count
    finally:
        conn.close()


def poll_subscription(sub):
    """Poll a single subscription for new articles.

    Creates pending episodes for any unseen articles.
    Returns the number of new episodes created.
    """
    sub_id = sub["id"]
    feed_url = sub["feed_url"]
    user_id = sub["user_id"]
    voice = sub["default_voice"]

    log.info("Polling subscription %d: %s", sub_id, feed_url)
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        log.warning("Feed parse error for %s: %s", feed_url, feed.bozo_exception)

    conn = get_db()
    new_count = 0
    try:
        # Update feed title if we got one
        if feed.feed.get("title") and not sub["title"]:
            conn.execute(
                "UPDATE subscriptions SET title = ? WHERE id = ?",
                (feed.feed["title"], sub_id),
            )

        for entry in feed.entries:
            link = entry.get("link", "")
            if not link:
                continue

            # Check if already seen
            seen = conn.execute(
                "SELECT id FROM seen_articles WHERE subscription_id = ? AND article_url = ?",
                (sub_id, link),
            ).fetchone()
            if seen:
                continue

            # New article: create episode and mark as seen
            title = entry.get("title", link)
            episode = create_episode(user_id, title, link, voice)
            conn.execute(
                "INSERT INTO seen_articles (subscription_id, article_url, episode_id) VALUES (?, ?, ?)",
                (sub_id, link, episode["id"]),
            )
            new_count += 1
            log.info("New article from subscription %d: %s", sub_id, title)

        # Update last_polled_at
        conn.execute(
            "UPDATE subscriptions SET last_polled_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (sub_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return new_count


def poll_all_due():
    """Poll all subscriptions that are due. Returns total new episodes created."""
    subs = get_due_subscriptions()
    if not subs:
        return 0

    total = 0
    for sub in subs:
        try:
            total += poll_subscription(sub)
        except Exception:
            log.exception("Error polling subscription %d: %s", sub["id"], sub["feed_url"])
    return total
