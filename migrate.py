"""Migration script: import episodes from old feed.xml into SQLite.

Parses the existing mp3/feed.xml, creates a default user, inserts episodes,
and copies MP3 files from mp3/ to data/mp3/. Also imports any MP3 files in
mp3/ that aren't referenced in the feed.

Usage:
    uv run python migrate.py [--username NAME] [--voice VOICE]
"""

import argparse
import os
import re
import shutil
import time
from xml.etree.ElementTree import parse

from app.config import DEFAULT_VOICE, MP3_DIR
from app.db import init_db, create_user, get_db


OLD_MP3_DIR = "mp3"
OLD_FEED = os.path.join(OLD_MP3_DIR, "feed.xml")


def _parse_source_url(description):
    """Try to extract original source URL from old feed description text."""
    if not description:
        return ""
    match = re.search(r"original source was (https?://\S+)", description)
    if match:
        return match.group(1)
    return ""


def _rfc2822_to_iso(date_str):
    """Convert RFC 2822 date to ISO 8601."""
    try:
        t = time.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", t)
    except (ValueError, TypeError):
        return None


def migrate(username, voice):
    init_db()

    # Create the default user
    user = create_user(username, voice)
    print(f"Created user '{username}'")
    print(f"  API key:    {user['api_key']}")
    print(f"  Feed token: {user['feed_token']}")

    imported_files = set()
    conn = get_db()

    # Parse old feed.xml if it exists
    if os.path.exists(OLD_FEED):
        tree = parse(OLD_FEED)
        root = tree.getroot()
        channel = root.find("channel")

        for item in channel.findall("item"):
            title = item.find("title").text or "Untitled"
            enclosure = item.find("enclosure")
            pub_date_el = item.find("pubDate")
            desc_el = item.find("description")

            mp3_filename = None
            file_size = None
            if enclosure is not None:
                url = enclosure.get("url", "")
                mp3_filename = url.split("/")[-1] if "/" in url else url
                file_size = int(enclosure.get("length", 0)) or None

            source_url = _parse_source_url(desc_el.text if desc_el is not None else "")
            published_at = _rfc2822_to_iso(pub_date_el.text) if pub_date_el is not None else None

            # Copy MP3 to new location if it exists
            status = "done"
            if mp3_filename:
                old_path = os.path.join(OLD_MP3_DIR, mp3_filename)
                new_path = os.path.join(MP3_DIR, mp3_filename)
                if os.path.exists(old_path):
                    shutil.copy2(old_path, new_path)
                    file_size = file_size or os.path.getsize(new_path)
                    imported_files.add(mp3_filename)
                else:
                    # MP3 not available locally
                    status = "error"

            conn.execute(
                """INSERT INTO episodes
                   (user_id, title, source_url, mp3_filename, file_size, voice, status, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], title, source_url or "", mp3_filename, file_size, voice, status, published_at),
            )
            print(f"  [{status}] {title}")

        conn.commit()
        print(f"\nImported {len(imported_files)} episodes from feed.xml")
    else:
        print(f"No feed.xml found at {OLD_FEED}")

    # Import any remaining MP3s not in the feed
    if os.path.isdir(OLD_MP3_DIR):
        extra = 0
        for f in sorted(os.listdir(OLD_MP3_DIR)):
            if not f.endswith(".mp3") or f in imported_files:
                continue
            old_path = os.path.join(OLD_MP3_DIR, f)
            new_path = os.path.join(MP3_DIR, f)
            shutil.copy2(old_path, new_path)
            file_size = os.path.getsize(new_path)
            title = f.replace(".mp3", "").replace("_", " ").title()
            conn.execute(
                """INSERT INTO episodes
                   (user_id, title, source_url, mp3_filename, file_size, voice, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], title, "", f, file_size, voice, "done"),
            )
            extra += 1
            print(f"  [extra] {title}")
        conn.commit()
        if extra:
            print(f"Imported {extra} extra MP3 files not in feed.xml")

    conn.close()
    print(f"\nDone! Start the server with: uv run python -m app.serve")
    print(f"Add articles at: /add?key={user['api_key']}")
    print(f"RSS feed at:     /feed/{user['feed_token']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate old feed.xml episodes to SQLite")
    parser.add_argument("--username", default="admin", help="Username for default user (default: admin)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Default voice (default: {DEFAULT_VOICE})")
    args = parser.parse_args()
    migrate(args.username, args.voice)
