"""Dynamic per-user RSS 2.0 podcast feed generation from database."""

import time
from xml.etree.ElementTree import Element, SubElement, tostring

from app.config import SITE_URL
from app.db import get_episodes_for_user


def generate_feed(user):
    """Generate RSS 2.0 XML for a user's completed episodes.

    Returns XML bytes with proper content type for podcast apps.
    """
    feed_url = f"{SITE_URL}/feed/{user['feed_token']}"

    rss = Element("rss", {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
    })
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = f"{user['username']}'s Reader Podcast"
    SubElement(channel, "link").text = feed_url
    SubElement(channel, "description").text = "Articles converted to audio with Reader Podcast"
    SubElement(channel, "language").text = "en"

    SubElement(channel, "itunes:block").text = "Yes"
    owner = SubElement(channel, "itunes:owner")
    SubElement(owner, "itunes:name").text = user["username"]

    image = SubElement(channel, "image")
    SubElement(image, "title").text = f"{user['username']}'s Reader Podcast"
    SubElement(image, "url").text = f"{SITE_URL}/logo.jpg"
    SubElement(image, "link").text = feed_url

    episodes = get_episodes_for_user(user["id"], status="done")
    for ep in episodes:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "link").text = ep["source_url"]
        SubElement(item, "description").text = (
            f"Audio version of: {ep['source_url']}"
        )

        audio_url = f"{SITE_URL}/mp3/{ep['mp3_filename']}"
        SubElement(item, "enclosure", {
            "url": audio_url,
            "length": str(ep["file_size"] or 0),
            "type": "audio/mpeg",
        })

        if ep["published_at"]:
            pub_date = _iso_to_rfc2822(ep["published_at"])
        else:
            pub_date = _iso_to_rfc2822(ep["created_at"])
        SubElement(item, "pubDate").text = pub_date

        SubElement(item, "guid", isPermaLink="false").text = ep["mp3_filename"]

    return tostring(rss, encoding="unicode", xml_declaration=True)


def _iso_to_rfc2822(iso_str):
    """Convert ISO 8601 timestamp to RFC 2822 format for RSS pubDate."""
    try:
        t = time.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", t)
    except (ValueError, TypeError):
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
