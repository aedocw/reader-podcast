from flask import Flask, request, send_file, redirect, url_for, render_template_string
import os
import get_content
import read_content
import write_feed
import time
from xml.etree.ElementTree import parse


app = Flask(__name__)

# Directory to store MP3 files
MP3_DIR = 'mp3'

os.makedirs(MP3_DIR, exist_ok=True)

# This should come from env var?
speakers = ["af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa", "bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", "bm_george", "bm_lewis",]

def get_existing_episodes():
    try:
        tree = parse("feed.xml")
        root = tree.getroot()
        channel = root.find("channel")
        episodes = []
        for item in channel.findall("item"):
            title = item.find("title").text
            pub_date = item.find("pubDate").text
            episodes.append((title, pub_date))
        return episodes
    except FileNotFoundError:
        return []

# Template for the add URL form
form_template = """
<!doctype html>
<title>Add URL</title>
<h1>Add a new article to the podcast feed</h1>
<form method=post enctype=multipart/form-data>
  <input type=text name=url placeholder="Enter URL" required>
  <select name=speaker>
    {% for speaker in speakers %}
      <option value="{{ speaker }}">{{ speaker }}</option>
    {% endfor %}
  </select>
  <input type=submit value=Submit>
</form>
{% if message %}
<p>{{ message }}</p>
{% endif %}
<h2>Existing Podcasts</h2>
<ul>
{% for title, pub_date in episodes %}
  <li><strong>{{ title }}</strong> - {{ pub_date }}</li>
{% endfor %}
</ul>
"""

@app.route('/feed.xml')
def feed():
    return send_file('feed.xml', mimetype='application/rss+xml')

@app.route('/add', methods=['GET', 'POST'])
def add_url():
    message = ''
    if request.method == 'POST':
        url = request.form['url']
        speaker = request.form.get('speaker') or "af_heart"
        speed = 1.1
        timestamp = int(time.time())
        filename = f"article_{timestamp}.mp3"
        
        try:
            title, paragraphs = get_content.fetch(url)
            paragraphs.insert(0, title)
            read_content.read_article(paragraphs, speaker, os.path.join(MP3_DIR, filename), speed)
            write_feed.append_to_feed(title, f"http://127.0.0.1:5000/mp3/{filename}", filename)

            message = f"Successfully added '{title}' to the feed."
            return redirect(url_for('add_url'))
        except Exception as e:
            message = f"An error occurred: {e}"

    episodes = get_existing_episodes()
    # Pass speakers list to the template
    return render_template_string(form_template, message=message, episodes=episodes, speakers=speakers)

@app.route('/mp3/<path:filename>')
def serve_mp3(filename):
    file_path = os.path.join(MP3_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='audio/mpeg')
    else:
        return "File not found", 404

@app.route('/')
def home():
    return 'Welcome to the Podcast Web Service. Visit /feed.xml to view the feed, /add to add a new URL, or /mp3/<filename> to stream an episode.'

if __name__ == '__main__':
    app.run(debug=True)
