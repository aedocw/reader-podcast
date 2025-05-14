import get_content
import read_content
import write_feed
import time
import sys
import warnings

warnings.filterwarnings("ignore", module="torch")

if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    print("Specify URL to read as argument")
    exit()

# Directory to store MP3 files
MP3_DIR = 'mp3'

os.makedirs(MP3_DIR, exist_ok=True)


speaker = "af_heart"
speed = 1.1
timestamp = int(time.time())
filename = f"article_{timestamp}.mp3"

title, paragraphs = get_content.fetch(url)
paragraphs.insert(0, title)
#print(f"Reading {title} to {filename}, {len(paragraphs)} paragraphs")
read_content.read_article(paragraphs, speaker, os.path.join(MP3_DIR, filename), speed)
write_feed.append_to_feed(title, f"http://127.0.0.1:5000/mp3/{filename}", filename)
