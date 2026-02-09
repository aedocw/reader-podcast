import os

from dotenv import load_dotenv

load_dotenv()

SITE_URL = os.getenv("SITE_URL", os.getenv("URL", "http://localhost:8025")).rstrip("/")
ADMIN_KEY = os.getenv("ADMIN_KEY", os.getenv("KEY", ""))
PORT = int(os.getenv("PORT", "8025"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/reader.db")
MP3_DIR = os.getenv("MP3_DIR", "data/mp3")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en-US-AndrewNeural")
RSS_POLL_INTERVAL_SECONDS = int(os.getenv("RSS_POLL_INTERVAL_SECONDS", "3600"))
