"""YouTube audio download via yt-dlp."""

import logging
import os

import yt_dlp

log = logging.getLogger(__name__)

_YOUTUBE_HOSTS = ("youtube.com/watch", "youtube.com/shorts/", "youtu.be/")


def is_youtube_url(url):
    return any(h in url for h in _YOUTUBE_HOSTS)


def get_info(url):
    """Fetch video metadata without downloading. Returns dict with title, uploader, duration_seconds."""
    opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title": info.get("title", "Unknown"),
        "uploader": info.get("uploader") or info.get("channel", ""),
        "duration": info.get("duration"),  # seconds, may be None
    }


def download_audio(url, output_path):
    """Download audio from a YouTube URL, convert to MP3 at output_path. Returns file size in bytes."""
    # yt-dlp outtmpl wants the path without extension; it appends .mp3 after postprocessing
    base = output_path[:-4] if output_path.endswith(".mp3") else output_path
    opts = {
        "format": "bestaudio/best",
        "outtmpl": base + ".%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return os.path.getsize(output_path)


def format_duration(seconds):
    """Format an integer number of seconds as H:MM:SS or M:SS."""
    if seconds is None:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
