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

speaker = "af_heart"
speed = 1.1
timestamp = int(time.time())
filename = f"article_{timestamp}.mp3"

title, paragraphs = get_content.fetch(url)
paragraphs.insert(0, title)
#print(f"Reading {title} to {filename}, {len(paragraphs)} paragraphs")
read_content.read_article(paragraphs, speaker, filename, speed)
write_feed.append_to_feed(title, url, filename)